import os
import re
import shutil
from pathlib import Path
from typing import Optional
from app.config import settings
from app.utils.errors import ValidationError
from app.utils.logger import logger


class FileService:
    @staticmethod
    def sanitize_filename(filename: str, max_length: int = 200) -> str:
        """
        Sanitizes untrusted filenames from external media sites:
        - Removes directory traversal (/, \\, ..)
        - Removes control characters and null bytes
        - Replaces filesystem-illegal characters (: * ? " < > |)
        - Removes leading/trailing dots and whitespace
        - Truncates safely preserving file extension
        """
        if not filename or not isinstance(filename, str):
            filename = "media_download"

        # Strip null bytes and control chars
        clean = "".join(ch for ch in filename if ord(ch) >= 32 and ch != '\x7f')

        # Replace path separators and illegal characters with underscores
        clean = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', clean)

        # Collapse multiple underscores/spaces
        clean = re.sub(r'[\s_]+', '_', clean).strip(" ._")

        if not clean:
            clean = "media_download"

        # Split stem and extension
        p = Path(clean)
        ext = p.suffix
        stem = p.stem

        # Extension length check
        if len(ext) > 15:
            ext = ext[:15]

        # Truncate stem if total exceeds max_length
        allowed_stem_len = max(10, max_length - len(ext))
        if len(stem) > allowed_stem_len:
            stem = stem[:allowed_stem_len].rstrip(" ._")

        final_name = f"{stem}{ext}" if ext else stem
        return final_name

    @staticmethod
    def sanitize_filename_template(template: str) -> str:
        """
        Sanitizes custom yt-dlp filename template to strictly prevent directory traversal,
        absolute paths, and invalid filesystem characters.
        """
        if not template or not isinstance(template, str):
            return "%(title).150B.%(ext)s"

        # Disallow directory separators, null bytes, and parent references
        clean = template.replace("..", "").replace("/", "").replace("\\", "").replace("\0", "").strip()
        # Remove colon/drive letters
        clean = re.sub(r'^[a-zA-Z]:', '', clean)
        clean = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', clean)

        # Ensure safe fallback if cleaned string has no valid extension or is empty
        if not clean or not ("%" in clean):
            return "%(title).150B.%(ext)s"

        return clean[:100]

    @staticmethod
    def get_safe_file_path(base_dir: Path | str, relative_name: str) -> Path:
        """
        Resolves path and guarantees it resides within base_dir (prevents directory traversal).
        """
        base = Path(base_dir).resolve()
        # Disallow traversal sequences explicitly
        if ".." in relative_name or "/" in relative_name or "\\" in relative_name:
            # Check if sanitized or purely a safe filename
            relative_name = FileService.sanitize_filename(relative_name)

        target = (base / relative_name).resolve()
        if not target.is_relative_to(base):
            logger.error(f"Path traversal detected: {relative_name} against {base}")
            raise ValidationError("Invalid file path: path traversal detected.")

        return target

    @staticmethod
    def ensure_directories() -> None:
        """Ensures that base downloads and temp directories exist with write permissions."""
        settings.download_path.mkdir(parents=True, exist_ok=True)
        settings.temp_path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def get_job_temp_dir(job_id: str) -> Path:
        """Returns the isolated temporary directory for a specific job."""
        safe_id = FileService.sanitize_filename(job_id)
        temp_dir = settings.temp_path / safe_id
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir

    @staticmethod
    def cleanup_temp_dir(temp_dir: Path | str) -> None:
        """Safely removes an isolated job temporary directory."""
        try:
            path = Path(temp_dir).resolve()
            # Ensure it is strictly inside the configured temp_path
            if path.is_relative_to(settings.temp_path) and path != settings.temp_path and path.exists():
                shutil.rmtree(path, ignore_errors=True)
                logger.info(f"Cleaned up temporary directory: {path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp dir {temp_dir}: {e}")

    @staticmethod
    def format_bytes(size: int | float) -> str:
        """Returns human-readable string for byte size."""
        if not size or size < 0:
            return "0 B"
        units = ["B", "KB", "MB", "GB", "TB"]
        idx = 0
        val = float(size)
        while val >= 1024.0 and idx < len(units) - 1:
            val /= 1024.0
            idx += 1
        return f"{val:.1f} {units[idx]}"
