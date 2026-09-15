import os
import re
import shutil
from pathlib import Path
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Support ASHORIN_* and legacy MEDIA_DOWNLOADER_* environment variables
for _k, _v in list(os.environ.items()):
    if _k.startswith("ASHORIN_"):
        _canonical = _k[len("ASHORIN_"):]
        if _canonical not in os.environ:
            os.environ[_canonical] = _v
    elif _k.startswith("MEDIA_DOWNLOADER_"):
        _canonical = _k[len("MEDIA_DOWNLOADER_"):]
        if _canonical not in os.environ and f"ASHORIN_{_canonical}" not in os.environ:
            os.environ[_canonical] = _v


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

    DOWNLOAD_DIR: str = Field(default="/media/Downloads")
    TEMP_DIR: str = Field(default="/data/temp")

    MAX_CONCURRENT_DOWNLOADS: int = Field(default=2, ge=1, le=10)
    DOWNLOAD_RETENTION: int = Field(default=86400, ge=0)  # legacy seconds (0 = disabled)
    DOWNLOAD_RETENTION_ENABLED: bool = Field(default=False)
    DOWNLOAD_RETENTION_DAYS: int = Field(default=7)
    TEMP_RETENTION: int = Field(default=3600, ge=0)        # seconds (0 = disabled)

    YTDLP_AUTO_UPDATE: bool = Field(default=True)
    YTDLP_UPDATE_INTERVAL: int = Field(default=86400, ge=60)
    YTDLP_UPDATE_CHANNEL: str = Field(default="stable")

    MAX_DOWNLOAD_SIZE: str = Field(default="10G")
    DOWNLOAD_TIMEOUT: int = Field(default=3600, ge=30)  # seconds
    ANALYSIS_TIMEOUT: int = Field(default=45, ge=10)    # seconds

    LOG_LEVEL: str = Field(default="INFO")

    DATA_DIR: str = Field(default="/data/app")
    MAX_QUEUE_SIZE: int = Field(default=100, ge=10, le=1000)
    MAX_BATCH_URLS: int = Field(default=100, ge=1, le=500)
    MAX_PLAYLIST_ITEMS: int = Field(default=5000, ge=1, le=10000)
    DEFAULT_PROFILE: str = Field(default="recommended")
    GLOBAL_BANDWIDTH_LIMIT: int = Field(default=0, ge=0)  # 0 = unlimited, in bytes/s

    ENABLE_LIBRARY: bool = Field(default=True)
    ENABLE_SCHEDULER: bool = Field(default=True)
    ENABLE_WEBHOOKS: bool = Field(default=True)
    ENABLE_NOTIFICATIONS: bool = Field(default=True)
    ENABLE_BROWSER_API: bool = Field(default=True)

    # Media Discovery & TMDB Configuration
    MEDIA_DISCOVERY_ENABLED: bool = Field(default=False)
    TMDB_API_KEY: Optional[str] = Field(default=None)
    TMDB_ENABLED: bool = Field(default=True)

    # Prowlarr Integration (Phase 2)
    PROWLARR_ENABLED: bool = Field(default=False)
    PROWLARR_URL: Optional[str] = Field(default=None)
    PROWLARR_API_KEY: Optional[str] = Field(default=None)
    PROWLARR_TIMEOUT_SECONDS: int = Field(default=60, ge=2, le=300)

    # Phase 6: Automatic Monitoring & Scheduled Search
    MONITORING_ENABLED: bool = Field(default=False)
    MONITORING_INTERVAL_HOURS: int = Field(default=6)
    MONITORING_MAX_CONCURRENCY: int = Field(default=3, ge=1, le=5)
    MONITORING_MAX_TARGETS_PER_CYCLE: int = Field(default=30, ge=5, le=50)
    MONITORING_COOLDOWN_HOURS: int = Field(default=6, ge=1, le=48)
    MONITORING_HISTORY_RETENTION_DAYS: int = Field(default=30, ge=7, le=90)
    MONITORING_SEARCH_MOVIES: bool = Field(default=True)
    MONITORING_SEARCH_EPISODES: bool = Field(default=True)

    # Phase 7A: Automatic Release Selection + Safe Automatic Missing-Media Downloads
    AUTOMATION_ENABLED: bool = Field(default=False)
    AUTOMATION_DRY_RUN: bool = Field(default=False)
    AUTOMATION_MIN_SCORE: int = Field(default=75, ge=0, le=100)
    AUTOMATION_MIN_SEEDERS: int = Field(default=5, ge=0)
    AUTOMATION_MAX_RELEASE_SIZE_GB: float = Field(default=20.0, ge=0.1)
    AUTOMATION_MIN_FREE_SPACE_GB: float = Field(default=20.0, ge=0.0)
    AUTOMATION_MAX_DOWNLOADS_PER_CYCLE: int = Field(default=3, ge=1, le=50)
    AUTOMATION_MAX_DOWNLOADS_PER_DAY: int = Field(default=10, ge=1, le=200)
    AUTOMATION_MAX_CONCURRENT_DOWNLOADS: int = Field(default=2, ge=1, le=10)
    AUTOMATION_COOLDOWN_HOURS: int = Field(default=6, ge=1, le=48)
    AUTOMATION_MAX_TOTAL_SIZE_PER_CYCLE_GB: float = Field(default=30.0, ge=0.1)
    AUTOMATION_MAX_TOTAL_SIZE_PER_DAY_GB: float = Field(default=100.0, ge=0.1)
    AUTOMATION_REQUIRE_COMPATIBLE_RELEASE: bool = Field(default=True)
    AUTOMATION_HISTORY_RETENTION_DAYS: int = Field(default=30, ge=7, le=90)
    AUTOMATION_EXCLUDED_WORDS: List[str] = Field(default_factory=list)
    AUTOMATION_EXCLUDED_REGEX: Optional[str] = Field(default=None)
    AUTOMATION_PAUSED: bool = Field(default=False)
    AUTOMATION_QUALITY_UPGRADES_ENABLED: bool = Field(default=False)

    # BitTorrent Configuration
    TORRENT_ENABLED: bool = Field(default=True)
    MAX_ACTIVE_TORRENTS: int = Field(default=2, ge=1, le=20)
    MAX_TORRENT_SIZE: str = Field(default="100G")
    MAX_TORRENT_FILE_SIZE: str = Field(default="10M")
    MAX_TORRENT_FILES: int = Field(default=10000, ge=1, le=100000)
    TORRENT_STORAGE_DIR: Optional[str] = None
    TORRENT_METADATA_DIR: Optional[str] = None
    DEFAULT_SEEDING_MODE: str = Field(default="stop")  # stop, ratio_1, ratio_2, time_30m, time_2h, indefinite
    TORRENT_PEER_LIMIT: int = Field(default=100, ge=10, le=1000)
    TORRENT_DOWNLOAD_LIMIT: int = Field(default=0, ge=0)  # 0 = unlimited bytes/s
    TORRENT_UPLOAD_LIMIT: int = Field(default=0, ge=0)    # 0 = unlimited bytes/s
    TORRENT_METADATA_TIMEOUT: int = Field(default=180, ge=5, le=3600)  # Metadata acquisition timeout in seconds (Section 14)
    MAX_METADATA_JOBS: int = Field(default=4, ge=1, le=20)  # Bounded metadata acquisition concurrency (Section 35)
    DEFAULT_TORRENT_TRACKERS: str = Field(
        default="udp://tracker.opentrackr.org:1337/announce,udp://open.tracker.cl:1337/announce,udp://tracker.openbittorrent.com:6969/announce,udp://open.stealth.si:80/announce,udp://tracker.torrent.eu.org:451/announce"
    )

    YTDLP_PATH: Optional[str] = None
    FFMPEG_PATH: Optional[str] = None

    @field_validator("MAX_CONCURRENT_DOWNLOADS")
    @classmethod
    def validate_concurrent(cls, v: int) -> int:
        if v < 1:
            return 1
        return v

    @field_validator("DOWNLOAD_RETENTION_DAYS")
    @classmethod
    def validate_retention_days(cls, v: int) -> int:
        if v not in (7, 14, 21, 30):
            return 7
        return v

    @property
    def max_download_size_bytes(self) -> int:
        return parse_bytes(self.MAX_DOWNLOAD_SIZE)

    @property
    def max_torrent_size_bytes(self) -> int:
        return parse_bytes(self.MAX_TORRENT_SIZE)

    @property
    def max_torrent_file_size_bytes(self) -> int:
        return parse_bytes(self.MAX_TORRENT_FILE_SIZE)

    @property
    def torrent_metadata_path(self) -> Path:
        p = Path(self.TORRENT_METADATA_DIR) if self.TORRENT_METADATA_DIR else self.data_path / "torrents"
        try:
            p.mkdir(parents=True, exist_ok=True)
            return p.resolve()
        except Exception:
            return p

    @property
    def default_torrent_trackers_list(self) -> List[str]:
        if not self.DEFAULT_TORRENT_TRACKERS:
            return []
        return [t.strip() for t in self.DEFAULT_TORRENT_TRACKERS.split(",") if t.strip()]

    @property
    def download_path(self) -> Path:
        try:
            from app.services.storage_service import StorageService
            return StorageService.get_downloads_dir()
        except Exception:
            return Path(self.DOWNLOAD_DIR)

    @property
    def temp_path(self) -> Path:
        try:
            from app.services.settings_service import settings_service
            custom = settings_service.get_storage_folder("temp")
            if custom:
                p = Path(custom)
                try:
                    p.mkdir(parents=True, exist_ok=True)
                    return p.resolve()
                except Exception:
                    pass
        except Exception:
            pass
        p = Path(self.TEMP_DIR)
        try:
            p.mkdir(parents=True, exist_ok=True)
            return p.resolve()
        except Exception:
            if Path("/data").exists() and os.access("/data", os.W_OK):
                return p
            try:
                local_fallback = Path(__file__).parent.parent.parent / "temp"
                local_fallback.mkdir(parents=True, exist_ok=True)
                return local_fallback.resolve()
            except Exception:
                return p

    @property
    def library_path(self) -> Path:
        try:
            from app.services.storage_service import StorageService
            return StorageService.get_library_dir()
        except Exception:
            return Path("/media/Library")

    @property
    def torrent_storage_path(self) -> Path:
        try:
            from app.services.storage_service import StorageService
            return StorageService.get_torrents_dir()
        except Exception:
            return Path("/media/Torrents")

    @property
    def import_storage_path(self) -> Path:
        try:
            from app.services.storage_service import StorageService
            return StorageService.get_imports_dir()
        except Exception:
            return Path("/media/Imports")

    @property
    def archive_path(self) -> Path:
        p = self.temp_path / "archives"
        try:
            p.mkdir(parents=True, exist_ok=True)
            return p.resolve()
        except Exception:
            return p

    @property
    def data_path(self) -> Path:
        target = Path(self.DATA_DIR)
        try:
            target.mkdir(parents=True, exist_ok=True)
            return target.resolve()
        except Exception:
            if Path("/data").exists():
                return target
            try:
                local_fallback = Path(__file__).parent.parent.parent / "app-data"
                local_fallback.mkdir(parents=True, exist_ok=True)
                return local_fallback.resolve()
            except Exception:
                return target

    @property
    def db_path(self) -> Path:
        return self.data_path / "ashorin.db"

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
