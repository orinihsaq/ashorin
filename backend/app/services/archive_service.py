import os
import re
import shutil
import time
import zipfile
from pathlib import Path
from typing import List, Optional

from app.config import settings
from app.services.file_service import FileService
from app.utils.errors import SecurityError, ValidationError
from app.utils.logger import logger


class ArchiveService:
    """
    Manages generation, caching, and cleanup of ZIP archives for multi-file torrents and collections.
    """

    CACHE_TTL_SECONDS: int = 600  # Reuse existing zip if generated within 10 minutes

    @classmethod
    def get_archive_path(cls, job_id: str, archive_name: str) -> Path:
        safe_job_id = FileService.sanitize_filename(job_id)
        safe_name = FileService.sanitize_filename(archive_name)
        if not safe_name.lower().endswith(".zip"):
            safe_name = f"{safe_name}.zip"
        return settings.archive_path / f"{safe_job_id}_{safe_name}"

    @classmethod
    def resolve_content_root(cls, directory: Path | str) -> Path:
        """
        Determines the actual finalized content root directory.
        If directory contains exactly one child directory and no loose files,
        and all completed files reside inside that child directory, return the child directory.
        """
        path = Path(directory).resolve()
        if not path.exists() or not path.is_dir():
            return path
        try:
            direct_children = [c for c in path.iterdir() if not c.name.startswith(".")]
            if len(direct_children) == 1 and direct_children[0].is_dir():
                child_dir = direct_children[0]
                child_files = [f for f in child_dir.rglob("*") if f.is_file() and not f.name.endswith((".part", ".ytdl", ".temp", ".tmp", ".zip"))]
                parent_files = [f for f in path.glob("*") if f.is_file()]
                if child_files and not parent_files:
                    return child_dir
        except Exception as e:
            logger.warning(f"Error checking content root for {path}: {e}")
        return path

    @classmethod
    def get_torrent_archive_metadata(
        cls,
        job_id: str,
        archive_name: str,
        source_dir: Path | str,
    ) -> dict:
        """Returns metadata about the archive (Section 21)."""
        source_path = cls.resolve_content_root(source_dir)
        target_zip = cls.get_archive_path(job_id, archive_name).resolve()
        file_count = 0
        if source_path.exists() and source_path.is_dir():
            file_count = sum(1 for f in source_path.rglob("*") if f.is_file() and not f.name.endswith((".part", ".ytdl", ".temp", ".tmp", ".zip")))
        archive_size = target_zip.stat().st_size if target_zip.exists() else 0
        return {
            "archive_name": archive_name if archive_name.lower().endswith(".zip") else f"{archive_name}.zip",
            "archive_path": str(target_zip),
            "file_count": file_count,
            "archive_size": archive_size,
        }

    @classmethod
    def create_torrent_zip(
        cls,
        source_dir: Path | str,
        archive_name: str,
        job_id: str,
        force_recreate: bool = False,
    ) -> Path:
        """
        Creates or retrieves a cached ZIP archive of a multi-file torrent directory.
        Preserves folder structures with top-level folder, rejects path traversal and symlink escapes,
        excludes partial/temporary files, checks content freshness, and writes atomically.
        """
        raw_path = Path(source_dir).resolve()
        if not raw_path.exists():
            logger.error(f"archive_source={raw_path} exists=false is_directory=false recursive_files=0")
            raise ValidationError(f"Source directory does not exist or is not a directory: {raw_path}")

        if not raw_path.is_dir():
            logger.error(f"archive_source={raw_path} exists=true is_directory=false recursive_files=0")
            raise ValidationError(f"Source path is not a directory: {raw_path}")

        # Path security check: Ensure source_path resides within configured download or data path
        base_dl = settings.download_path.resolve()
        if not raw_path.is_relative_to(base_dl):
            logger.error(f"Directory traversal attempt: {raw_path} is outside download dir {base_dl}")
            raise SecurityError("Forbidden: Source directory is outside download boundary.")

        if raw_path == base_dl:
            logger.error("Forbidden: Root download directory cannot be archived directly.")
            raise SecurityError("Forbidden: Root download directory cannot be archived directly.")

        # Resolve content root (Section 40)
        source_path = cls.resolve_content_root(raw_path)

        target_zip = cls.get_archive_path(job_id, archive_name).resolve()
        base_archive = settings.archive_path.resolve()
        base_archive.mkdir(parents=True, exist_ok=True)

        # Ensure target_zip is within archive_path
        if not target_zip.is_relative_to(base_archive):
            raise SecurityError("Forbidden: Archive destination outside archive path.")

        # Collect files recursively
        files_to_zip: List[Path] = []
        newest_mtime = 0.0

        for fpath in source_path.rglob("*"):
            if not fpath.is_file():
                continue
            # Ignore temporary/partial torrent pieces and zip files
            if fpath.name.endswith((".part", ".ytdl", ".temp", ".torrent", ".tmp", ".zip")):
                continue

            try:
                resolved_file = fpath.resolve()
                # Check symlink escape
                if not resolved_file.is_relative_to(base_dl) or not resolved_file.is_relative_to(source_path):
                    logger.warning(f"Skipping symlink escaping source dir: {fpath} -> {resolved_file}")
                    continue
            except Exception as e:
                logger.warning(f"Error resolving path {fpath}: {e}")
                continue

            files_to_zip.append(fpath)
            try:
                st_mtime = fpath.stat().st_mtime
                if st_mtime > newest_mtime:
                    newest_mtime = st_mtime
            except Exception:
                pass

        # Diagnostic logging (Section 15)
        logger.info(
            f"archive_source={source_path} exists=true is_directory=true "
            f"file_count={len(files_to_zip)} recursive_files={len(files_to_zip)}"
        )

        if not files_to_zip:
            raise ValidationError("No valid completed files found in torrent directory to archive.")

        # Check cache: If archive exists, is non-empty, newer than CACHE_TTL_SECONDS,
        # and newer than newest file in directory (Section 25, 26)
        now = time.time()
        if not force_recreate and target_zip.exists() and target_zip.stat().st_size > 0:
            zip_mtime = target_zip.stat().st_mtime
            age = now - zip_mtime
            if age < cls.CACHE_TTL_SECONDS and zip_mtime >= newest_mtime:
                logger.debug(f"Reusing cached archive {target_zip.name} (age: {int(age)}s)")
                return target_zip
            else:
                logger.info(f"Invalidating stale archive {target_zip.name} (zip_mtime={zip_mtime}, newest_file={newest_mtime})")

        # Write to temporary file first for atomic creation
        temp_zip = target_zip.with_suffix(".zip.tmp")
        try:
            with zipfile.ZipFile(temp_zip, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
                for fpath in sorted(files_to_zip):
                    rel = fpath.relative_to(source_path)
                    # Section 12: Preserve top-level folder inside ZIP
                    top_folder = source_path.name
                    arcname = Path(top_folder) / rel
                    # Defense in depth: check arcname doesn't contain '..'
                    if ".." in str(arcname):
                        raise SecurityError(f"Traversal sequence in archive entry: {arcname}")
                    zf.write(fpath, arcname=str(arcname))

            temp_zip.replace(target_zip)
            logger.info(f"Successfully created torrent archive: {target_zip.name} ({len(files_to_zip)} files)")
            return target_zip
        except Exception as e:
            if temp_zip.exists():
                temp_zip.unlink(missing_ok=True)
            logger.exception(f"Failed to create ZIP archive for {source_path}: {e}")
            raise

    @classmethod
    def cleanup_stale_archives(cls, max_age_seconds: int = 900) -> int:
        """
        Removes temporary and expired ZIP archives in settings.archive_path older than max_age_seconds.
        """
        archive_dir = settings.archive_path
        if not archive_dir.exists():
            return 0

        now = time.time()
        removed_count = 0
        try:
            for item in archive_dir.iterdir():
                try:
                    if not item.is_file():
                        continue
                    if item.name.endswith((".zip", ".tmp", ".zip.tmp")):
                        age = now - item.stat().st_mtime
                        if age > max_age_seconds:
                            item.unlink(missing_ok=True)
                            removed_count += 1
                            logger.info(f"Removed stale archive: {item.name} (age: {int(age)}s)")
                except Exception as ex:
                    logger.warning(f"Error checking archive file {item}: {ex}")
        except Exception as e:
            logger.error(f"Error scanning archive directory for cleanup: {e}")

        return removed_count
