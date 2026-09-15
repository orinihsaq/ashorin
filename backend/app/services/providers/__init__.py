from app.services.providers.base import BaseDownloadProvider, DownloadProvider
from app.services.providers.torrent_provider import TorrentProvider, torrent_provider
from app.services.providers.ytdlp_provider import YtDlpProvider, ytdlp_provider


def get_provider(name: str) -> BaseDownloadProvider:
    if name == "ytdlp":
        return ytdlp_provider
    elif name == "torrent":
        return torrent_provider
    raise ValueError(f"Unknown provider: {name}")


__all__ = [
    "BaseDownloadProvider",
    "DownloadProvider",
    "YtDlpProvider",
    "TorrentProvider",
    "ytdlp_provider",
    "torrent_provider",
    "get_provider",
]
