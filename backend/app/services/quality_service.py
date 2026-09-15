import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from app.config import settings
from app.repositories.media_repository import MediaRepository
from app.repositories.quality_repository import QualityRepository
from app.services.webhook_service import WebhookService
from app.utils.logger import logger


RESOLUTION_HIERARCHY: Dict[str, int] = {
    "4320p": 4320,
    "8k": 4320,
    "2160p": 2160,
    "4k": 2160,
    "1440p": 1440,
    "2k": 1440,
    "1080p": 1080,
    "720p": 720,
    "480p": 480,
    "360p": 360,
    "240p": 240,
    "144p": 144,
}


class QualityService:
    @staticmethod
    def parse_resolution_height(res_str: Optional[str]) -> int:
        """Extracts vertical pixel height from resolution strings (e.g. '1080p', '1920x1080')."""
        if not res_str:
            return 0
        cleaned = res_str.lower().strip()
        if cleaned in RESOLUTION_HIERARCHY:
            return RESOLUTION_HIERARCHY[cleaned]

        if "x" in cleaned:
            parts = cleaned.split("x")
            try:
                return int(parts[1].replace("p", "").strip())
            except Exception:
                pass

        digits = "".join(filter(str.isdigit, cleaned))
        if digits:
            try:
                val = int(digits)
                if val > 100 and val <= 4320:
                    return val
            except Exception:
                pass
        return 0

    @classmethod
    def is_upgrade(
        cls, current_res: Optional[str], available_res: Optional[str],
        current_fps: Optional[int] = None, available_fps: Optional[int] = None
    ) -> Tuple[bool, str]:
        """Compares two video quality levels. Returns (is_better, reason)."""
        curr_h = cls.parse_resolution_height(current_res)
        avail_h = cls.parse_resolution_height(available_res)

        if avail_h > curr_h and curr_h > 0:
            return True, f"Higher resolution available: {available_res} (was {current_res})"

        if avail_h == curr_h and avail_h > 0:
            if available_fps and current_fps and available_fps > current_fps:
                return True, f"Higher frame rate available: {available_fps}fps (was {current_fps}fps)"

        return False, "Current version meets or exceeds available stream"

    @classmethod
    def calculate_storage_impact(
        cls, current_bytes: Optional[int], new_bytes: Optional[int]
    ) -> Tuple[int, str]:
        """Calculates difference in storage and formatted summary."""
        curr = current_bytes or 0
        new = new_bytes or 0
        diff = new - curr
        from app.utils.formatting import format_bytes
        if diff > 0:
            return diff, f"+{format_bytes(diff)} additional storage"
        elif diff < 0:
            return diff, f"-{format_bytes(abs(diff))} storage reduction"
        return 0, "No storage difference"

    @classmethod
    def check_and_register_upgrade(
        cls, media_id: str, new_res: str, new_filesize: Optional[int], source_url: str
    ) -> bool:
        """Checks if new stream is an upgrade over library media; registers if true."""
        media = MediaRepository.get_media(media_id)
        if not media:
            return False

        curr_res = media.get("resolution") or "720p"
        is_better, reason = cls.is_upgrade(curr_res, new_res)
        if is_better:
            avail_h = cls.parse_resolution_height(new_res)
            QualityRepository.mark_upgrade_available(
                media_id=media_id,
                upgrade_height=avail_h,
                upgrade_filesize=new_filesize,
                upgrade_source_url=source_url,
            )
            WebhookService.dispatch_event("media.upgrade_available", {
                "media_id": media_id,
                "title": media.get("title"),
                "current_resolution": curr_res,
                "available_resolution": new_res,
                "reason": reason,
            })
            return True
        return False

    @classmethod
    async def apply_safe_upgrade(cls, media_id: str, new_job_id: str, new_file_path: Path) -> bool:
        """
        Safely replaces an existing library file with an upgraded version.
        Guarantees:
        1. Validates new file exists and size > 0.
        2. Preserves metadata, favorites, protection flags.
        3. Deletes old file only AFTER new file verified.
        4. Updates library catalog and quality target.
        """
        media = MediaRepository.get_media(media_id)
        if not media:
            logger.error(f"Cannot apply upgrade: media {media_id} not found")
            return False

        if not new_file_path.exists() or new_file_path.stat().st_size == 0:
            logger.error(f"Cannot apply upgrade: new file {new_file_path} is missing or empty")
            return False

        old_rel_path = media.get("relative_path")
        old_abs_path = settings.download_path / old_rel_path if old_rel_path else None

        try:
            new_stat = new_file_path.stat()
            rel_new = str(new_file_path.relative_to(settings.download_path))

            # Update library item with new path, filesize, and job_id
            from app.db.database import get_db
            with get_db() as conn:
                conn.execute(
                    """
                    UPDATE media_library SET
                        job_id = ?,
                        filename = ?,
                        relative_path = ?,
                        filesize = ?,
                        downloaded_at = ?
                    WHERE id = ?
                    """,
                    (new_job_id, new_file_path.name, rel_new, new_stat.st_size, new_stat.st_mtime, media_id),
                )

            # Safely remove old file if different from new
            if old_abs_path and old_abs_path.exists() and old_abs_path != new_file_path:
                try:
                    old_abs_path.unlink(missing_ok=True)
                    logger.info(f"Safely retired previous media file: {old_abs_path}")
                except Exception as e:
                    logger.warning(f"Could not delete old media file {old_abs_path}: {e}")

            QualityRepository.update_upgrade_status(media_id, "UPGRADED")
            WebhookService.dispatch_event("media.upgraded", {
                "media_id": media_id,
                "title": media.get("title"),
                "new_file": new_file_path.name,
                "filesize": new_stat.st_size,
            })
            return True
        except Exception as e:
            logger.error(f"Error applying safe upgrade for {media_id}: {e}")
            return False
