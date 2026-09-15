import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Set
from app.config import settings
from app.models.schemas import DownloadConfig, DownloadRequest
from app.repositories.media_repository import MediaRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.recipe_repository import RecipeRepository
from app.repositories.watcher_repository import WatcherRepository
from app.services.duplicate_detector import DuplicateDetector
from app.services.job_manager import job_manager
from app.services.quality_service import QualityService
from app.services.security import SecurityService
from app.services.webhook_service import WebhookService
from app.services.yt_dlp import YtDlpService
from app.utils.logger import logger


class WatcherService:
    _active_sync_ids: Set[str] = set()
    _background_task: Optional[asyncio.Task] = None
    _stop_event = asyncio.Event()

    @classmethod
    def start_scheduler(cls) -> None:
        """Starts the background loop for periodic watcher checks."""
        if cls._background_task is None or cls._background_task.done():
            cls._stop_event.clear()
            cls._background_task = asyncio.create_task(cls._scheduler_loop())
            logger.info("Collection Watcher background scheduler started.")

    @classmethod
    def stop_scheduler(cls) -> None:
        """Stops the watcher scheduler loop gracefully."""
        cls._stop_event.set()
        if cls._background_task:
            cls._background_task.cancel()
            logger.info("Collection Watcher scheduler stopped.")

    @classmethod
    async def _scheduler_loop(cls) -> None:
        while not cls._stop_event.is_set():
            try:
                now = time.time()
                due_watchers = WatcherRepository.get_due_watchers(now)
                for watcher in due_watchers:
                    # Run sync concurrently without blocking loop
                    asyncio.create_task(cls.sync_watcher(watcher["id"], is_manual=False))
            except Exception as e:
                logger.error(f"Error in watcher scheduler loop: {e}")

            # Check every 30 seconds
            try:
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break

    @classmethod
    async def sync_watcher(cls, watcher_id: str, is_manual: bool = False) -> Dict[str, Any]:
        """
        Executes a watcher sync run:
        1. Overlap lock
        2. SSRF re-validation
        3. Metadata extraction without downloading media
        4. Comparison against local library & active queue
        5. Queue new items and upgrades
        6. Webhooks & run logging
        """
        if watcher_id in cls._active_sync_ids:
            logger.warning(f"Watcher {watcher_id} is already syncing. Skipping overlapping run.")
            return {"status": "skipped", "reason": "Sync already in progress"}

        watcher = WatcherRepository.get_watcher(watcher_id)
        if not watcher:
            return {"status": "error", "reason": "Watcher not found"}

        if watcher["status"] == "PAUSED" and not is_manual:
            return {"status": "skipped", "reason": "Watcher is paused"}

        cls._active_sync_ids.add(watcher_id)
        now = time.time()
        run_id = WatcherRepository.record_run({
            "watcher_id": watcher_id,
            "started_at": now,
            "status": "RUNNING",
        })

        WebhookService.dispatch_event("watcher.sync_started", {
            "watcher_id": watcher_id,
            "watcher_name": watcher["name"],
            "source_url": watcher["source_url"],
            "manual": is_manual,
        })

        try:
            # 1. Security check: revalidate URL
            validated_url = SecurityService.validate_url(watcher["source_url"])

            # 2. Extract collection metadata (flat playlist extraction)
            media_analysis = await YtDlpService.analyze_url(validated_url)
            raw_entries = [e.model_dump() if hasattr(e, 'model_dump') else (dict(e) if isinstance(e, dict) else e.__dict__) for e in media_analysis.entries] if media_analysis.is_playlist else [
                {
                    "id": getattr(media_analysis, "playlist_id", None) or "single",
                    "title": media_analysis.title,
                    "url": media_analysis.url,
                    "duration": media_analysis.duration,
                    "video_options": media_analysis.video_options,
                }
            ]

            # 3. Resolve profile & recipe
            profile_data = None
            storage_folder = None
            if watcher.get("recipe_id"):
                recipe = RecipeRepository.get_recipe(watcher["recipe_id"])
                if recipe:
                    profile_data = ProfileRepository.get_profile(recipe["profile_id"])
                    storage_folder = recipe.get("storage_folder")

            if not profile_data:
                profile_data = ProfileRepository.get_profile(watcher.get("profile_id", "recommended"))
            if not profile_data:
                profile_data = ProfileRepository.get_default_profile()

            base_config = DownloadConfig(**profile_data.get("config", {}))

            # 4. Compare items
            new_items: List[Dict[str, Any]] = []
            duplicates_count = 0
            upgrades_count = 0
            items_seen = len(raw_entries)

            for entry in raw_entries:
                item_url = entry.get("url") or validated_url
                is_dup, dup_reason, dup_item = DuplicateDetector.check_duplicate(item_url)

                if is_dup:
                    duplicates_count += 1
                    # Quality upgrade check
                    if watcher.get("upgrade_policy") != "never" and dup_item and isinstance(dup_item, dict):
                        curr_res = dup_item.get("resolution")
                        target_res = watcher.get("target_quality", "1080p")
                        is_better, _ = QualityService.is_upgrade(curr_res, target_res)
                        if is_better:
                            upgrades_count += 1
                            QualityService.check_and_register_upgrade(
                                media_id=dup_item["id"],
                                new_res=target_res,
                                new_filesize=None,
                                source_url=item_url,
                            )
                else:
                    new_items.append(entry)

            # 5. Queue new items if enabled
            queued_count = 0
            if watcher.get("download_new", True) and new_items:
                for item in new_items:
                    try:
                        item_url = item.get("url") or validated_url
                        req = DownloadRequest(
                            url=item_url,
                            title=item.get("title"),
                            config=base_config,
                            priority="NORMAL",
                            profile_id=profile_data.get("id"),
                        )
                        await job_manager.create_job(req)
                        queued_count += 1
                    except Exception as e:
                        logger.error(f"Watcher {watcher_id} failed to queue item {item.get('title')}: {e}")

            # 6. Calculate next check interval
            interval = watcher.get("interval_seconds", 21600)
            next_check = time.time() + interval
            result_summary = f"{items_seen} seen · {len(new_items)} new · {duplicates_count} existing · {queued_count} queued"

            # Update Watcher & Run record
            WatcherRepository.update_watcher(watcher_id, {
                "items_tracked": items_seen,
                "items_downloaded": watcher.get("items_downloaded", 0) + queued_count,
                "last_checked": time.time(),
                "next_check": next_check,
                "last_sync_result": result_summary,
                "consecutive_failures": 0,
                "last_error": None,
                "status": "ACTIVE" if watcher["status"] != "PAUSED" else "PAUSED",
            })

            WatcherRepository.update_run(run_id, {
                "completed_at": time.time(),
                "status": "COMPLETED",
                "items_seen": items_seen,
                "new_items": len(new_items),
                "duplicates": duplicates_count,
                "upgrades": upgrades_count,
                "queued": queued_count,
                "failed": 0,
                "details": {
                    "queued_titles": [i.get("title") for i in new_items[:10]],
                },
            })

            # Webhooks
            if len(new_items) > 0:
                WebhookService.dispatch_event("watcher.new_items", {
                    "watcher_id": watcher_id,
                    "watcher_name": watcher["name"],
                    "new_count": len(new_items),
                    "queued_count": queued_count,
                })

            WebhookService.dispatch_event("watcher.sync_completed", {
                "watcher_id": watcher_id,
                "watcher_name": watcher["name"],
                "items_seen": items_seen,
                "queued_count": queued_count,
                "summary": result_summary,
            })

            return {
                "status": "success",
                "items_seen": items_seen,
                "new_items": len(new_items),
                "duplicates": duplicates_count,
                "upgrades": upgrades_count,
                "queued": queued_count,
                "summary": result_summary,
            }

        except Exception as e:
            logger.error(f"Watcher sync failed for {watcher_id}: {e}")
            consec_fails = watcher.get("consecutive_failures", 0) + 1
            # Exponential backoff up to 8x the interval
            backoff_mult = min(2 ** min(consec_fails, 3), 8)
            interval = watcher.get("interval_seconds", 21600) * backoff_mult
            next_check = time.time() + interval

            WatcherRepository.update_watcher(watcher_id, {
                "last_checked": time.time(),
                "next_check": next_check,
                "consecutive_failures": consec_fails,
                "last_error": str(e),
                "last_sync_result": f"Sync failed: {str(e)}",
            })

            WatcherRepository.update_run(run_id, {
                "completed_at": time.time(),
                "status": "FAILED",
                "error": str(e),
            })

            WebhookService.dispatch_event("watcher.sync_failed", {
                "watcher_id": watcher_id,
                "watcher_name": watcher["name"],
                "error": str(e),
                "retry_in_seconds": interval,
            })

            return {"status": "error", "error": str(e), "retry_in_seconds": interval}

        finally:
            cls._active_sync_ids.discard(watcher_id)
