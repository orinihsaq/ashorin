"""
Base download provider interface.
Both YtDlpProvider and TorrentProvider implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union
from app.models.schemas import AnalyzeResponse, TorrentAnalysisResponse


class BaseDownloadProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier for this provider ('ytdlp' or 'torrent')."""
        pass

    @abstractmethod
    async def analyze(self, input_value: str) -> Union[AnalyzeResponse, TorrentAnalysisResponse]:
        """
        Inspects input and acquires metadata.
        For HTTP/HTTPS: runs yt-dlp analysis.
        For magnet / torrent: acquires BitTorrent metadata.
        """
        pass


# Backward compatibility alias
DownloadProvider = BaseDownloadProvider
