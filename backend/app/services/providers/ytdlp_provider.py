"""
yt-dlp Media Provider for ashoriN:
Handles HTTP and HTTPS media URLs with strict SSRF defense and yt-dlp metadata extraction.
"""

from typing import Union
from app.models.schemas import AnalyzeResponse
from app.services.providers.base import BaseDownloadProvider
from app.services.security import SecurityService
from app.services.yt_dlp import YtDlpService
from app.utils.logger import logger


class YtDlpProvider(BaseDownloadProvider):
    @property
    def provider_name(self) -> str:
        return "ytdlp"

    async def analyze(self, input_value: str) -> AnalyzeResponse:
        """
        Validates HTTP/HTTPS URL with SSRF defense and runs yt-dlp metadata extraction.
        Never called for magnet URIs or .torrent files.
        """
        valid_url = SecurityService.validate_http_url(input_value)
        logger.info(f"YtDlpProvider analyzing validated HTTP/HTTPS URL: {valid_url[:60]}")
        return await YtDlpService.analyze_url(valid_url)


ytdlp_provider = YtDlpProvider()
