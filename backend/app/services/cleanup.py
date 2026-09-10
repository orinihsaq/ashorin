import asyncio
import shutil
import time
from pathlib import Path
from app.config import settings
from app.utils.logger import logger


class CleanupService:
    @staticmethod
    def cleanup_downloads(retention_seconds: int) -> int:
        """
        Deletes files in DOWNLOAD_DIR that were modified longer ago than retention_seconds.
        If retention_seconds <= 0, cleanup is disabled.
        Returns count of removed files.
        """
        if retention_seconds <= 0:
            return 0

        now = time.time()
        download_dir = settings.download_path
        if not download_dir.exists():
            return 0

        deleted_count = 0
        try:
            for item in download_dir.iterdir():
                if item.is_file():
                    try:
                        mtime = item.stat().st_mtime
                        if (now - mtime) > retention_seconds:
                            item.unlink(missing_ok=True)
                            deleted_count += 1
                            logger.info(f"Cleaned up expired download file: {item.name} (age: {int(now - mtime)}s)")
                    except Exception as e:
                        logger.warning(f"Error checking/deleting file {item}: {e}")
        except Exception as e:
            logger.error(f"Error scanning download directory during cleanup: {e}")

        return deleted_count

    @staticmethod
    def cleanup_temp(retention_seconds: int) -> int:
        """
        Deletes temporary directories and files in TEMP_DIR older than retention_seconds.
        If retention_seconds <= 0, cleanup is disabled.
        Returns count of removed entries.
        """
        if retention_seconds <= 0:
            return 0

        now = time.time()
        temp_dir = settings.temp_path
        if not temp_dir.exists():
            return 0

        deleted_count = 0
        try:
            for item in temp_dir.iterdir():
                try:
                    mtime = item.stat().st_mtime
                    if (now - mtime) > retention_seconds:
                        if item.is_dir():
                            shutil.rmtree(item, ignore_errors=True)
                        else:
                            item.unlink(missing_ok=True)
                        deleted_count += 1
                        logger.info(f"Cleaned up expired temp entry: {item.name}")
                except Exception as e:
                    logger.warning(f"Error cleaning temp item {item}: {e}")
        except Exception as e:
            logger.error(f"Error scanning temp directory during cleanup: {e}")

        return deleted_count

    @classmethod
    async def run_periodic_cleanup(cls) -> None:
        """Background worker loop running cleanup every 60 seconds."""
        logger.info("Starting background file cleanup service.")
        while True:
            try:
                await asyncio.sleep(60)
                cls.cleanup_downloads(settings.DOWNLOAD_RETENTION)
                cls.cleanup_temp(settings.TEMP_RETENTION)
            except asyncio.CancelledError:
                logger.info("File cleanup service received stop signal.")
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup worker: {e}")
