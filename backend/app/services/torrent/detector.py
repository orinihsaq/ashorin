"""
Unified input detector for ashoriN:
Classifies inputs into 'ytdlp', 'torrent_magnet', or 'torrent_file'.
"""

from typing import Union
from app.services.input_router import detect_input_type, InputType, get_provider_for_input


class InputDetector:
    @classmethod
    def detect(cls, input_data: Union[str, bytes]) -> str:
        """
        Determines the appropriate download provider for the given input.
        Returns:
            'torrent_magnet' - Valid BitTorrent magnet link
            'torrent_file'   - Raw .torrent file bytes or filepath ending with .torrent
            'ytdlp'          - Standard HTTP/HTTPS or supported media URL
        """
        itype = detect_input_type(input_data)
        if itype == InputType.MAGNET_URI:
            return "torrent_magnet"
        elif itype == InputType.TORRENT_FILE:
            return "torrent_file"
        return "ytdlp"

    @classmethod
    def get_provider(cls, input_data: Union[str, bytes]) -> str:
        """Returns 'torrent' or 'ytdlp'."""
        itype = detect_input_type(input_data)
        if itype in (InputType.MAGNET_URI, InputType.TORRENT_FILE):
            return "torrent"
        return "ytdlp"

    @classmethod
    def get_input_type(cls, input_data: Union[str, bytes]) -> str:
        """Returns 'magnet', 'torrent_file', or 'url'."""
        itype = detect_input_type(input_data)
        if itype == InputType.MAGNET_URI:
            return "magnet"
        elif itype == InputType.TORRENT_FILE:
            return "torrent_file"
        return "url"
