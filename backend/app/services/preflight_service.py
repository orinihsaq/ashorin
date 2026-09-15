import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.config import settings
from app.models.schemas import PreflightItemDetail, PreflightResponse
from app.repositories.media_repository import MediaRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.recipe_repository import RecipeRepository
from app.repositories.rule_repository import RuleRepository
from app.services.duplicate_detector import DuplicateDetector
from app.services.quality_service import QualityService
from app.services.security import SecurityService
from app.services.yt_dlp import YtDlpService
from app.utils.formatting import format_bytes
from app.utils.logger import logger


class PreflightService:
    @classmethod
    async def analyze_preflight(
        cls,
        url: str,
        profile_id: Optional[str] = None,
        recipe_id: Optional[str] = None,
        selected_indices: Optional[List[int]] = None,
        dry_run: bool = False,
    ) -> PreflightResponse:
        validated_url = SecurityService.validate_url(url)

        # 1. Resolve Recipe / Profile
        resolved_recipe = None
        resolved_profile = None

        if recipe_id:
            resolved_recipe = RecipeRepository.get_recipe(recipe_id)
            if resolved_recipe:
                resolved_profile = ProfileRepository.get_profile(resolved_recipe["profile_id"])

        if not resolved_profile:
            if profile_id:
                resolved_profile = ProfileRepository.get_profile(profile_id)
            else:
                rule_match = RuleRepository.evaluate_rules(url=validated_url)
                if rule_match.get("matched") and rule_match.get("profile_id"):
                    resolved_profile = ProfileRepository.get_profile(rule_match["profile_id"])

        if not resolved_profile:
            resolved_profile = ProfileRepository.get_default_profile()

        # 2. Extract collection / media metadata
        media_analysis = await YtDlpService.analyze_url(validated_url)
        is_playlist = media_analysis.is_playlist

        # 3. Disk Space Check
        usage = shutil.disk_usage(str(settings.download_path))
        disk_free = usage.free

        # 4. Process items
        items_details: List[PreflightItemDetail] = []
        new_count = 0
        existing_count = 0
        upgrade_count = 0
        unavailable_count = 0
        total_estimated_bytes = 0
        known_size = True

        raw_items = [e.model_dump() if hasattr(e, 'model_dump') else (dict(e) if isinstance(e, dict) else e.__dict__) for e in media_analysis.entries] if is_playlist else [
            {
                "index": 1,
                "title": media_analysis.title,
                "url": media_analysis.url,
                "duration": media_analysis.duration,
                "duration_string": media_analysis.duration_string,
                "video_options": media_analysis.video_options,
            }
        ]

        # Determine destination folder template
        dest_folder = "Downloads"
        if resolved_recipe and resolved_recipe.get("storage_folder"):
            dest_folder = resolved_recipe["storage_folder"]
        elif is_playlist:
            clean_title = media_analysis.title or "Playlist"
            dest_folder = f"Playlists/{clean_title}"

        explanations = []

        for item_idx, entry in enumerate(raw_items, start=1):
            if selected_indices and item_idx not in selected_indices:
                continue

            item_title = entry.get("title") or f"Item {item_idx}"
            item_url = entry.get("url") or validated_url

            # Check duplicate in library / queue
            is_dup, dup_reason, dup_item = DuplicateDetector.check_duplicate(item_url)

            # Check quality upgrade candidate
            item_status = "new"
            reason = None
            current_res = None
            avail_res = None
            current_lib_id = None

            if is_dup:
                if dup_item and isinstance(dup_item, dict) and "resolution" in dup_item:
                    current_lib_id = dup_item.get("id")
                    current_res = dup_item.get("resolution")
                    avail_res = resolved_recipe.get("target_quality") if resolved_recipe else "1080p"
                    is_better, upgrade_reason = QualityService.is_upgrade(current_res, avail_res)
                    if is_better:
                        item_status = "upgrade"
                        reason = upgrade_reason
                        upgrade_count += 1
                    else:
                        item_status = "existing"
                        reason = dup_reason
                        existing_count += 1
                else:
                    item_status = "existing"
                    reason = dup_reason
                    existing_count += 1
            else:
                new_count += 1

            # Estimate size
            est_bytes = None
            duration_secs = entry.get("duration") or 180
            # Rough approximation: 1080p ~1.5 MB/s, 720p ~0.8 MB/s, audio ~0.15 MB/s
            if resolved_profile and resolved_profile.get("config", {}).get("audio_mode") == "audio_only":
                est_bytes = int(duration_secs * 150_000)
            else:
                est_bytes = int(duration_secs * 1_200_000)

            total_estimated_bytes += est_bytes

            items_details.append(
                PreflightItemDetail(
                    index=item_idx,
                    title=item_title,
                    url=item_url,
                    media_id=str(entry.get("id")) if entry.get("id") else None,
                    status=item_status,
                    reason=reason,
                    estimated_bytes=est_bytes,
                    estimated_bytes_formatted=format_bytes(est_bytes) if est_bytes else None,
                    current_library_id=current_lib_id,
                    current_resolution=current_res,
                    available_resolution=avail_res,
                )
            )

        if existing_count > 0:
            explanations.append(f"{existing_count} items already exist in your local library or active download queue and will be skipped.")
        if upgrade_count > 0:
            explanations.append(f"{upgrade_count} items match existing media but have higher quality versions available.")
        if new_count > 0:
            explanations.append(f"{new_count} new media items ready for download.")

        # Storage safety evaluation (minimum 500MB safety buffer)
        safety_buffer = 500 * 1024 * 1024
        if disk_free < total_estimated_bytes:
            storage_status = "critical"
            storage_msg = f"Insufficient disk space. Needed ~{format_bytes(total_estimated_bytes)}, but only {format_bytes(disk_free)} free."
        elif disk_free < (total_estimated_bytes + safety_buffer):
            storage_status = "warning"
            storage_msg = f"Low storage warning. Free space ({format_bytes(disk_free)}) will be nearly exhausted after this download."
        else:
            storage_status = "sufficient"
            storage_msg = f"Sufficient storage available ({format_bytes(disk_free)} free)."

        return PreflightResponse(
            title=media_analysis.title or "Media Collection",
            is_playlist=is_playlist,
            total_items=len(raw_items),
            selected_items=len(items_details),
            new_items_count=new_count,
            existing_items_count=existing_count,
            upgrade_items_count=upgrade_count,
            unavailable_items_count=unavailable_count,
            estimated_total_bytes=total_estimated_bytes if known_size else None,
            estimated_total_formatted=format_bytes(total_estimated_bytes),
            disk_free_bytes=disk_free,
            disk_free_formatted=format_bytes(disk_free),
            storage_status=storage_status,
            storage_message=storage_msg,
            resolved_profile_id=resolved_profile.get("id", "recommended"),
            resolved_profile_name=resolved_profile.get("name", "Recommended"),
            resolved_recipe_id=resolved_recipe.get("id") if resolved_recipe else None,
            resolved_recipe_name=resolved_recipe.get("name") if resolved_recipe else None,
            destination_folder=dest_folder,
            items=items_details,
            explanations=explanations,
        )
