import re
import shutil
from pathlib import Path
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_bytes(size_str: str) -> int:
    """Parse human readable size string like '10G', '500M', '1024K', or integer string to bytes."""
    size_str = str(size_str).strip().upper()
    match = re.match(r"^(\d+(?:\.\d+)?)\s*([KMGTPE]?B?)$", size_str)
    if not match:
        try:
            return int(size_str)
        except ValueError:
            raise ValueError(f"Invalid size string: {size_str}")

    num, unit = match.groups()
    val = float(num)
    unit = unit.rstrip("B")

    multipliers = {
        "": 1,
        "K": 1024,
        "M": 1024**2,
        "G": 1024**3,
        "T": 1024**4,
        "P": 1024**5,
        "E": 1024**6,
    }

    if unit not in multipliers:
        raise ValueError(f"Unknown size unit: {unit}")

    return int(val * multipliers[unit])


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "ashoriN"
    APP_VERSION: str = "1.0.0"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8080

    DOWNLOAD_DIR: str = Field(default="/data/downloads")
    TEMP_DIR: str = Field(default="/data/temp")

    MAX_CONCURRENT_DOWNLOADS: int = Field(default=2, ge=1, le=10)
    DOWNLOAD_RETENTION: int = Field(default=86400, ge=0)  # seconds (0 = disabled)
    TEMP_RETENTION: int = Field(default=3600, ge=0)        # seconds (0 = disabled)

    YTDLP_AUTO_UPDATE: bool = Field(default=True)
    YTDLP_UPDATE_INTERVAL: int = Field(default=86400, ge=60)
    YTDLP_UPDATE_CHANNEL: str = Field(default="stable")

    MAX_DOWNLOAD_SIZE: str = Field(default="10G")
    DOWNLOAD_TIMEOUT: int = Field(default=3600, ge=30)  # seconds
    ANALYSIS_TIMEOUT: int = Field(default=45, ge=10)    # seconds

    LOG_LEVEL: str = Field(default="INFO")

    YTDLP_PATH: Optional[str] = None
    FFMPEG_PATH: Optional[str] = None

    @field_validator("MAX_CONCURRENT_DOWNLOADS")
    @classmethod
    def validate_concurrent(cls, v: int) -> int:
        if v < 1:
            return 1
        return v

    @property
    def max_download_size_bytes(self) -> int:
        return parse_bytes(self.MAX_DOWNLOAD_SIZE)

    @property
    def download_path(self) -> Path:
        return Path(self.DOWNLOAD_DIR).resolve()

    @property
    def temp_path(self) -> Path:
        return Path(self.TEMP_DIR).resolve()

    def resolve_binaries(self) -> None:
        """Auto-detect yt-dlp and ffmpeg paths if not explicitly configured."""
        if not self.YTDLP_PATH:
            found = shutil.which("yt-dlp")
            if found:
                self.YTDLP_PATH = found
            else:
                # Check typical user and venv locations
                user_ytdlp = Path.home() / ".local/bin/yt-dlp"
                if user_ytdlp.exists():
                    self.YTDLP_PATH = str(user_ytdlp)
                else:
                    self.YTDLP_PATH = "yt-dlp"

        if not self.FFMPEG_PATH:
            found = shutil.which("ffmpeg")
            if found:
                self.FFMPEG_PATH = found
            else:
                user_ffmpeg = Path.home() / ".local/bin/ffmpeg"
                if user_ffmpeg.exists():
                    self.FFMPEG_PATH = str(user_ffmpeg)
                else:
                    self.FFMPEG_PATH = "ffmpeg"


settings = Settings()
settings.resolve_binaries()
