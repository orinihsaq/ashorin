"""
BitTorrent Provider for ashoriN:
Handles magnet URIs and .torrent files directly via dedicated torrent metadata resolution.
Guarantees that magnet links and .torrent files NEVER enter yt-dlp or HTTP/HTTPS URL checks.
"""

from typing import Union
from app.models.schemas import TorrentAnalysisResponse
from app.services.input_router import detect_input_type, InputType
from app.services.providers.base import BaseDownloadProvider
from app.services.torrent.torrent_service import torrent_service
from app.utils.errors import ValidationError
from app.utils.logger import logger


class TorrentProvider(BaseDownloadProvider):
    @property
    def provider_name(self) -> str:
        return "torrent"

    async def analyze(self, input_value: str) -> TorrentAnalysisResponse:
        """
        Analyzes a BitTorrent input (magnet URI or .torrent file).
        Bypasses yt-dlp analysis and HTTP/HTTPS URL validation entirely.
        """
        itype = detect_input_type(input_value)
        if itype == InputType.MAGNET_URI:
            logger.info("TorrentProvider analyzing magnet URI")
            return await torrent_service.analyze_magnet(input_value)
        elif itype == InputType.TORRENT_FILE:
            logger.info("TorrentProvider analyzing .torrent file")
            return await torrent_service.analyze_torrent_file(input_value)
        else:
            raise ValidationError("Input is not a valid BitTorrent magnet link or .torrent file.")


torrent_provider = TorrentProvider()
