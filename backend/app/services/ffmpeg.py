import asyncio
import re
import shutil
from typing import Optional, Tuple
from app.config import settings
from app.utils.logger import logger


class FFmpegService:
    _cached_version: Optional[str] = None
    _cached_available: Optional[bool] = None

    @classmethod
    def is_available(cls) -> bool:
        if cls._cached_available is not None:
            return cls._cached_available

        path = settings.FFMPEG_PATH or shutil.which("ffmpeg")
        cls._cached_available = bool(path and shutil.which(path))
        return cls._cached_available

    @classmethod
    async def get_version(cls) -> Tuple[bool, str]:
        """
        Executes ffmpeg -version using argument array without shell.
        Returns (is_available, version_string).
        """
        if cls._cached_version:
            return True, cls._cached_version

        ffmpeg_bin = settings.FFMPEG_PATH or shutil.which("ffmpeg") or "ffmpeg"
        try:
            proc = await asyncio.create_subprocess_exec(
                ffmpeg_bin,
                "-version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            if proc.returncode == 0 and stdout:
                first_line = stdout.decode("utf-8", errors="ignore").splitlines()[0]
                # Match e.g. "ffmpeg version 7.0.2-static" -> "7.0.2-static"
                match = re.search(r"ffmpeg version\s+([^\s]+)", first_line, re.IGNORECASE)
                version = match.group(1) if match else first_line[:40]
                cls._cached_version = version
                cls._cached_available = True
                return True, version
        except Exception as e:
            logger.warning(f"Failed to check FFmpeg version: {e}")

        cls._cached_available = False
        return False, "Not available"
