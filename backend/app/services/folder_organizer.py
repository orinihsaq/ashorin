import datetime
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from app.config import settings
from app.services.file_service import FileService
from app.utils.logger import logger


class FolderOrganizer:
    @classmethod
    def resolve_folder_path(
        cls,
        template: Optional[str],
        metadata: Dict[str, Any],
        is_playlist: bool = False,
    ) -> Tuple[Path, str]:
        """
        Resolves the output folder path from a template and metadata dictionary.
        Returns a tuple: (absolute_folder_path, relative_folder_str)
        Guarantees that the resulting directory remains strictly inside settings.download_path.
        """
        base_dir = settings.download_path.resolve()

        if is_playlist and metadata.get("playlist_title"):
            safe_playlist_folder = FileService.sanitize_filename(str(metadata["playlist_title"])) or "Playlist"
            folder = base_dir / safe_playlist_folder
            folder.mkdir(parents=True, exist_ok=True)
            return folder, safe_playlist_folder

        if not template or template.strip() in ("", "flat"):
            return base_dir, ""

        now = datetime.datetime.now()
        year = str(metadata.get("year") or now.year)
        month = f"{metadata.get('month') or now.month:02d}" if isinstance(metadata.get('month'), int) else f"{now.month:02d}"
        uploader = FileService.sanitize_filename(str(metadata.get("uploader") or "Unknown_Uploader")) or "Unknown_Uploader"
        extractor = FileService.sanitize_filename(str(metadata.get("extractor") or "generic")) or "generic"
        resolution = FileService.sanitize_filename(str(metadata.get("resolution") or "best")) or "best"

        # Preset shortcuts
        t_clean = template.strip().lower()
        if t_clean == "uploader":
            template = "%(uploader)s"
        elif t_clean == "date" or t_clean == "year_month":
            template = "%(year)s/%(month)s"
        elif t_clean == "extractor":
            template = "%(extractor)s"

        # Substitute tokens
        rendered = template
        rendered = rendered.replace("%(uploader)s", uploader)
        rendered = rendered.replace("%(year)s", year)
        rendered = rendered.replace("%(month)s", month)
        rendered = rendered.replace("%(extractor)s", extractor)
        rendered = rendered.replace("%(resolution)s", resolution)

        # Sanitize each folder segment
        segments = [s for s in rendered.split("/") if s.strip()]
        safe_segments = []
        for s in segments:
            clean_s = FileService.sanitize_filename(s)
            if clean_s and clean_s not in (".", ".."):
                safe_segments.append(clean_s)

        if not safe_segments:
            return base_dir, ""

        relative_str = "/".join(safe_segments)
        target_dir = base_dir.joinpath(*safe_segments)

        # Final path containment check
        try:
            resolved = target_dir.resolve()
            if not resolved.is_relative_to(base_dir):
                logger.warning(f"Path containment violation in folder organizer: {target_dir}")
                return base_dir, ""
            target_dir.mkdir(parents=True, exist_ok=True)
            return target_dir, relative_str
        except Exception as e:
            logger.error(f"Error resolving folder path: {e}")
            return base_dir, ""
