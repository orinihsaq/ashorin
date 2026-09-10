import asyncio
import re
import sys
import time
from typing import Optional, Tuple
import httpx
from app.config import settings
from app.services.yt_dlp import YtDlpService
from app.utils.logger import logger


def parse_version_tuple(v_str: str) -> Tuple[int, ...]:
    """Parse versions like '2026.08.30' or '2026.8.19' into sortable integer tuple."""
    if not v_str:
        return (0,)
    clean = re.sub(r"[^\d.]", "", v_str.strip())
    parts = []
    for p in clean.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    return tuple(parts) if parts else (0,)


class YtDlpUpdater:
    PYPI_URL = "https://pypi.org/pypi/yt-dlp/json"
    GITHUB_URL = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"

    _latest_version: Optional[str] = None
    _last_check_time: float = 0.0

    @classmethod
    async def fetch_latest_version(cls) -> Optional[str]:
        """Queries the official PyPI / GitHub API over HTTPS with strict timeout."""
        # Use cache if checked within the last 10 minutes
        now = time.time()
        if cls._latest_version and (now - cls._last_check_time) < 600:
            return cls._latest_version

        # 1. Try PyPI official JSON API first
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                res = await client.get(cls.PYPI_URL, headers={"Accept": "application/json", "User-Agent": "MediaDownloader/1.0"})
                if res.status_code == 200:
                    data = res.json()
                    version = data.get("info", {}).get("version")
                    if version:
                        cls._latest_version = version
                        cls._last_check_time = now
                        return version
        except Exception as e:
            logger.warning(f"Could not check PyPI for yt-dlp update: {e}")

        # 2. Fallback to GitHub official release API
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                res = await client.get(cls.GITHUB_URL, headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "MediaDownloader/1.0"})
                if res.status_code == 200:
                    data = res.json()
                    tag = data.get("tag_name") or data.get("name")
                    if tag:
                        clean_tag = tag.lstrip("v")
                        cls._latest_version = clean_tag
                        cls._last_check_time = now
                        return clean_tag
        except Exception as e:
            logger.warning(f"Could not check GitHub for yt-dlp update: {e}")

        return None

    @classmethod
    async def check_update_needed(cls) -> Tuple[bool, str, Optional[str]]:
        """
        Returns (is_update_available, current_version, latest_version).
        """
        current_ver = await YtDlpService.get_version()
        latest_ver = await cls.fetch_latest_version()

        if not latest_ver or latest_ver == "Unknown":
            return False, current_ver, None

        cur_tuple = parse_version_tuple(current_ver)
        lat_tuple = parse_version_tuple(latest_ver)

        update_available = lat_tuple > cur_tuple
        return update_available, current_ver, latest_ver

    @classmethod
    async def update_ytdlp(cls) -> Tuple[bool, str]:
        """
        Safely upgrades yt-dlp using pip without breaking existing binaries.
        Returns (success: bool, message: str).
        """
        is_needed, current_ver, latest_ver = await cls.check_update_needed()

        if not is_needed and latest_ver:
            return True, f"yt-dlp is already up to date ({current_ver})."

        logger.info(f"Updating yt-dlp from {current_ver} to {latest_ver or 'latest'}...")

        # Run pip upgrade using current python interpreter
        cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-cache-dir",
            "--upgrade",
            "yt-dlp",
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120.0)

            if proc.returncode == 0:
                new_ver = await YtDlpService.get_version()
                logger.info(f"Successfully upgraded yt-dlp to {new_ver}")
                cls._latest_version = new_ver
                return True, f"Successfully upgraded yt-dlp to version {new_ver}"
            else:
                err_text = stderr.decode("utf-8", errors="ignore")
                logger.error(f"Failed to upgrade yt-dlp: {err_text}")
                return False, f"Upgrade failed: {err_text[:200]}"
        except Exception as e:
            logger.error(f"Exception during yt-dlp update: {e}")
            return False, f"Update failed: {str(e)}"

    @classmethod
    async def startup_check(cls) -> None:
        """
        Non-blocking startup update check:
        If update fails or network is down, never prevents the app from running.
        """
        current_ver = await YtDlpService.get_version()
        logger.info(f"Current yt-dlp version: {current_ver}")

        if not settings.YTDLP_AUTO_UPDATE:
            logger.info("yt-dlp auto-update is disabled by configuration.")
            return

        logger.info("Checking for yt-dlp updates...")
        try:
            needed, cur, lat = await cls.check_update_needed()
            if needed:
                logger.info(f"New yt-dlp version found: {lat} (current: {cur}). Upgrading...")
                success, msg = await cls.update_ytdlp()
                if not success:
                    logger.warning(f"Startup update failed (proceeding anyway): {msg}")
            else:
                logger.info(f"yt-dlp is up to date ({cur}).")
        except Exception as e:
            logger.warning(f"yt-dlp startup check failed gracefully: {e}. Starting application anyway.")
