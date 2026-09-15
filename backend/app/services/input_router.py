"""
Canonical input detection and routing architecture for ashoriN.

Classifies all user inputs FIRST before any provider, security validator, or analyzer executes:
  - HTTP_URL      -> YtDlpProvider
  - HTTPS_URL     -> YtDlpProvider
  - MAGNET_URI    -> TorrentProvider
  - TORRENT_FILE  -> TorrentProvider
  - UNKNOWN       -> Clean validation error (never enters yt-dlp)
"""

from enum import Enum
from typing import Any, Dict, Optional, Tuple, Union
from app.utils.errors import ValidationError


class InputType(str, Enum):
    HTTP_URL = "HTTP_URL"
    HTTPS_URL = "HTTPS_URL"
    MAGNET_URI = "MAGNET_URI"
    TORRENT_FILE = "TORRENT_FILE"
    UNKNOWN = "UNKNOWN"


class ProviderType(str, Enum):
    YTDLP = "ytdlp"
    TORRENT = "torrent"


def detect_input_type(value: Union[str, bytes, None]) -> InputType:
    """
    Determines input type FIRST before any provider, analyzer, or HTTP validator runs.
    Guarantees that magnet links and torrent files never enter yt-dlp or HTTP SSRF checks.

    Returns one of:
      - InputType.HTTP_URL
      - InputType.HTTPS_URL
      - InputType.MAGNET_URI
      - InputType.TORRENT_FILE
      - InputType.UNKNOWN
    """
    if value is None:
        return InputType.UNKNOWN

    if isinstance(value, (bytes, bytearray)):
        if value.startswith(b"d") and b"4:info" in value[:1024]:
            return InputType.TORRENT_FILE
        return InputType.UNKNOWN

    if not isinstance(value, str):
        return InputType.UNKNOWN

    clean = value.strip()
    if not clean:
        return InputType.UNKNOWN

    lower = clean.lower()

    # Dedicated magnet scheme check
    if lower.startswith("magnet:"):
        return InputType.MAGNET_URI

    # Dedicated torrent file check (local path or file:// URI)
    if lower.endswith(".torrent") or (lower.startswith("file://") and lower.endswith(".torrent")):
        return InputType.TORRENT_FILE

    # Explicit HTTPS check
    if lower.startswith("https://"):
        return InputType.HTTPS_URL

    # Explicit HTTP check
    if lower.startswith("http://"):
        return InputType.HTTP_URL

    return InputType.UNKNOWN


def get_provider_for_input(value: Union[str, bytes, None]) -> str:
    """Returns 'torrent' or 'ytdlp' based on detected input type."""
    itype = detect_input_type(value)
    if itype in (InputType.MAGNET_URI, InputType.TORRENT_FILE):
        return "torrent"
    elif itype in (InputType.HTTP_URL, InputType.HTTPS_URL):
        return "ytdlp"
    raise ValidationError(
        "Unsupported input type. Only HTTP, HTTPS, magnet URIs, and .torrent files are supported."
    )


class InputRouter:
    """
    Routes user input to the correct provider:
      - HTTP/HTTPS   -> YtDlpProvider
      - MAGNET       -> TorrentProvider
      - TORRENT_FILE -> TorrentProvider
    """
    @classmethod
    def get_provider_type(cls, value: Union[str, bytes, None]) -> str:
        return get_provider_for_input(value)

    @classmethod
    def route_provider(cls, value: Union[str, bytes, None]):
        itype = detect_input_type(value)
        if itype in (InputType.HTTP_URL, InputType.HTTPS_URL):
            from app.services.providers.ytdlp_provider import ytdlp_provider
            return ytdlp_provider
        elif itype in (InputType.MAGNET_URI, InputType.TORRENT_FILE):
            from app.services.providers.torrent_provider import torrent_provider
            return torrent_provider
        else:
            raise ValidationError(
                "Unsupported input type. Only HTTP, HTTPS, magnet URIs, and .torrent files are supported."
            )
