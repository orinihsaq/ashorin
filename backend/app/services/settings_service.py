import json
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
from app.config import settings
from app.utils.errors import ValidationError
from app.utils.logger import logger

ALLOWED_RETENTION_DAYS: List[int] = [7, 14, 21, 30]
ALLOWED_MONITORING_INTERVAL_HOURS: List[int] = [1, 2, 4, 6, 12, 24]


class SettingsService:
    def __init__(self):
        self._retention_enabled: bool = bool(settings.DOWNLOAD_RETENTION_ENABLED)
        self._retention_days: int = int(settings.DOWNLOAD_RETENTION_DAYS) if settings.DOWNLOAD_RETENTION_DAYS in ALLOWED_RETENTION_DAYS else 7
        self._media_discovery_enabled: bool = bool(settings.MEDIA_DISCOVERY_ENABLED)
        self._tmdb_enabled: bool = bool(settings.TMDB_ENABLED)
        self._tmdb_api_key: Optional[str] = settings.TMDB_API_KEY
        self._prowlarr_enabled: bool = bool(settings.PROWLARR_ENABLED)
        self._prowlarr_url: Optional[str] = settings.PROWLARR_URL
        self._prowlarr_api_key: Optional[str] = settings.PROWLARR_API_KEY
        self._prowlarr_timeout_seconds: int = int(settings.PROWLARR_TIMEOUT_SECONDS)
        # Phase 6: Automatic Monitoring
        self._monitoring_enabled: bool = bool(settings.MONITORING_ENABLED)
        self._monitoring_interval_hours: int = int(settings.MONITORING_INTERVAL_HOURS) if settings.MONITORING_INTERVAL_HOURS in ALLOWED_MONITORING_INTERVAL_HOURS else 6
        self._monitoring_max_concurrency: int = int(settings.MONITORING_MAX_CONCURRENCY)
        self._monitoring_max_targets_per_cycle: int = int(settings.MONITORING_MAX_TARGETS_PER_CYCLE)
        self._monitoring_cooldown_hours: int = int(settings.MONITORING_COOLDOWN_HOURS)
        self._monitoring_history_retention_days: int = int(settings.MONITORING_HISTORY_RETENTION_DAYS)
        self._monitoring_search_movies: bool = bool(settings.MONITORING_SEARCH_MOVIES)
        self._monitoring_search_episodes: bool = bool(settings.MONITORING_SEARCH_EPISODES)
        # Phase 7A: Automatic Release Selection + Safe Automatic Missing-Media Downloads
        self._automation_enabled: bool = bool(settings.AUTOMATION_ENABLED)
        self._automation_dry_run: bool = bool(settings.AUTOMATION_DRY_RUN)
        self._automation_min_score: int = int(settings.AUTOMATION_MIN_SCORE)
        self._automation_min_seeders: int = int(settings.AUTOMATION_MIN_SEEDERS)
        self._automation_max_release_size_gb: float = float(settings.AUTOMATION_MAX_RELEASE_SIZE_GB)
        self._automation_min_free_space_gb: float = float(settings.AUTOMATION_MIN_FREE_SPACE_GB)
        self._automation_max_downloads_per_cycle: int = int(settings.AUTOMATION_MAX_DOWNLOADS_PER_CYCLE)
        self._automation_max_downloads_per_day: int = int(settings.AUTOMATION_MAX_DOWNLOADS_PER_DAY)
        self._automation_max_concurrent_downloads: int = int(settings.AUTOMATION_MAX_CONCURRENT_DOWNLOADS)
        self._automation_cooldown_hours: int = int(settings.AUTOMATION_COOLDOWN_HOURS)
        self._automation_max_total_size_per_cycle_gb: float = float(settings.AUTOMATION_MAX_TOTAL_SIZE_PER_CYCLE_GB)
        self._automation_max_total_size_per_day_gb: float = float(settings.AUTOMATION_MAX_TOTAL_SIZE_PER_DAY_GB)
        self._automation_require_compatible_release: bool = bool(settings.AUTOMATION_REQUIRE_COMPATIBLE_RELEASE)
        self._automation_history_retention_days: int = int(settings.AUTOMATION_HISTORY_RETENTION_DAYS)
        self._automation_excluded_words: List[str] = list(settings.AUTOMATION_EXCLUDED_WORDS)
        self._automation_excluded_regex: Optional[str] = settings.AUTOMATION_EXCLUDED_REGEX
        self._automation_paused: bool = bool(settings.AUTOMATION_PAUSED)
        self._automation_quality_upgrades_enabled: bool = bool(settings.AUTOMATION_QUALITY_UPGRADES_ENABLED)
        self._storage_folders: Dict[str, str] = {}
        self._initialized: bool = False

    def _get_default_storage_folders(self) -> Dict[str, str]:
        data_dir = Path("/data")
        if data_dir.exists():
            return {
                "downloads": "/data/downloads",
                "library": "/data/library",
                "torrents": "/data/torrents",
                "import": "/data/imports",
                "temp": "/data/temp",
            }
        base = settings.download_path.parent
        return {
            "downloads": str(settings.download_path),
            "library": str(base / "library"),
            "torrents": str(base / "torrents"),
            "import": str(base / "imports"),
            "temp": str(settings.temp_path),
        }

    def _get_storage_path(self) -> Path:
        """
        Determines the safe persistence path for runtime settings.
        Prefers persistent volume settings.data_path / "settings.json",
        falling back to /data/settings.json or /data/downloads/.settings.json.
        """
        try:
            dp = settings.data_path
            if dp.exists() and os.access(str(dp), os.W_OK):
                return dp / "settings.json"
        except Exception:
            pass
        data_dir = Path("/data")
        try:
            if data_dir.exists() and os.access(str(data_dir), os.W_OK):
                return data_dir / "settings.json"
        except Exception:
            pass
        return settings.download_path / ".settings.json"

    def init_settings(self) -> None:
        """Loads persisted settings from disk if available."""
        if self._initialized:
            return

        storage_path = self._get_storage_path()
        candidates = [
            storage_path,
            settings.data_path / "settings.json",
            Path("/data/settings.json"),
            settings.download_path / ".settings.json",
        ]

        target_file = None
        for candidate in candidates:
            try:
                if candidate and candidate.exists() and candidate.is_file():
                    target_file = candidate
                    break
            except Exception:
                continue

        if target_file and target_file.is_file():
            try:
                with open(target_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "retention_enabled" in data and isinstance(data["retention_enabled"], bool):
                        self._retention_enabled = data["retention_enabled"]
                    if "retention_days" in data and data["retention_days"] in ALLOWED_RETENTION_DAYS:
                        self._retention_days = int(data["retention_days"])
                    if "media_discovery_enabled" in data and isinstance(data["media_discovery_enabled"], bool):
                        self._media_discovery_enabled = data["media_discovery_enabled"]
                    if "tmdb_enabled" in data and isinstance(data["tmdb_enabled"], bool):
                        self._tmdb_enabled = data["tmdb_enabled"]
                    if "tmdb_api_key" in data and isinstance(data["tmdb_api_key"], str):
                        clean_k = data["tmdb_api_key"].strip()
                        self._tmdb_api_key = clean_k if clean_k else None
                    if "prowlarr_enabled" in data and isinstance(data["prowlarr_enabled"], bool):
                        self._prowlarr_enabled = data["prowlarr_enabled"]
                    if "prowlarr_url" in data and (isinstance(data["prowlarr_url"], str) or data["prowlarr_url"] is None):
                        clean_u = data["prowlarr_url"].strip() if isinstance(data["prowlarr_url"], str) else ""
                        self._prowlarr_url = clean_u if clean_u else None
                    if "prowlarr_api_key" in data and isinstance(data["prowlarr_api_key"], str):
                        clean_pk = data["prowlarr_api_key"].strip()
                        self._prowlarr_api_key = clean_pk if clean_pk else None
                    if "prowlarr_timeout_seconds" in data and isinstance(data["prowlarr_timeout_seconds"], (int, float)):
                        self._prowlarr_timeout_seconds = int(data["prowlarr_timeout_seconds"])
                    if "monitoring_enabled" in data and isinstance(data["monitoring_enabled"], bool):
                        self._monitoring_enabled = data["monitoring_enabled"]
                    if "monitoring_interval_hours" in data and data["monitoring_interval_hours"] in ALLOWED_MONITORING_INTERVAL_HOURS:
                        self._monitoring_interval_hours = int(data["monitoring_interval_hours"])
                    if "monitoring_max_concurrency" in data and isinstance(data["monitoring_max_concurrency"], (int, float)) and (1 <= int(data["monitoring_max_concurrency"]) <= 5):
                        self._monitoring_max_concurrency = int(data["monitoring_max_concurrency"])
                    if "monitoring_max_targets_per_cycle" in data and isinstance(data["monitoring_max_targets_per_cycle"], (int, float)) and (5 <= int(data["monitoring_max_targets_per_cycle"]) <= 50):
                        self._monitoring_max_targets_per_cycle = int(data["monitoring_max_targets_per_cycle"])
                    if "monitoring_cooldown_hours" in data and isinstance(data["monitoring_cooldown_hours"], (int, float)) and (1 <= int(data["monitoring_cooldown_hours"]) <= 48):
                        self._monitoring_cooldown_hours = int(data["monitoring_cooldown_hours"])
                    if "monitoring_history_retention_days" in data and isinstance(data["monitoring_history_retention_days"], (int, float)) and (7 <= int(data["monitoring_history_retention_days"]) <= 90):
                        self._monitoring_history_retention_days = int(data["monitoring_history_retention_days"])
                    if "monitoring_search_movies" in data and isinstance(data["monitoring_search_movies"], bool):
                        self._monitoring_search_movies = data["monitoring_search_movies"]
                    if "monitoring_search_episodes" in data and isinstance(data["monitoring_search_episodes"], bool):
                        self._monitoring_search_episodes = data["monitoring_search_episodes"]
                    # Phase 7A: Automation
                    if "automation_enabled" in data and isinstance(data["automation_enabled"], bool):
                        self._automation_enabled = data["automation_enabled"]
                    if "automation_dry_run" in data and isinstance(data["automation_dry_run"], bool):
                        self._automation_dry_run = data["automation_dry_run"]
                    if "automation_min_score" in data and isinstance(data["automation_min_score"], (int, float)) and 0 <= int(data["automation_min_score"]) <= 100:
                        self._automation_min_score = int(data["automation_min_score"])
                    if "automation_min_seeders" in data and isinstance(data["automation_min_seeders"], (int, float)) and int(data["automation_min_seeders"]) >= 0:
                        self._automation_min_seeders = int(data["automation_min_seeders"])
                    if "automation_max_release_size_gb" in data and isinstance(data["automation_max_release_size_gb"], (int, float)) and float(data["automation_max_release_size_gb"]) > 0:
                        self._automation_max_release_size_gb = float(data["automation_max_release_size_gb"])
                    if "automation_min_free_space_gb" in data and isinstance(data["automation_min_free_space_gb"], (int, float)) and float(data["automation_min_free_space_gb"]) >= 0:
                        self._automation_min_free_space_gb = float(data["automation_min_free_space_gb"])
                    if "automation_max_downloads_per_cycle" in data and isinstance(data["automation_max_downloads_per_cycle"], (int, float)) and 1 <= int(data["automation_max_downloads_per_cycle"]) <= 50:
                        self._automation_max_downloads_per_cycle = int(data["automation_max_downloads_per_cycle"])
                    if "automation_max_downloads_per_day" in data and isinstance(data["automation_max_downloads_per_day"], (int, float)) and 1 <= int(data["automation_max_downloads_per_day"]) <= 200:
                        self._automation_max_downloads_per_day = int(data["automation_max_downloads_per_day"])
                    if "automation_max_concurrent_downloads" in data and isinstance(data["automation_max_concurrent_downloads"], (int, float)) and 1 <= int(data["automation_max_concurrent_downloads"]) <= 10:
                        self._automation_max_concurrent_downloads = int(data["automation_max_concurrent_downloads"])
                    if "automation_cooldown_hours" in data and isinstance(data["automation_cooldown_hours"], (int, float)) and 1 <= int(data["automation_cooldown_hours"]) <= 48:
                        self._automation_cooldown_hours = int(data["automation_cooldown_hours"])
                    if "automation_max_total_size_per_cycle_gb" in data and isinstance(data["automation_max_total_size_per_cycle_gb"], (int, float)) and float(data["automation_max_total_size_per_cycle_gb"]) > 0:
                        self._automation_max_total_size_per_cycle_gb = float(data["automation_max_total_size_per_cycle_gb"])
                    if "automation_max_total_size_per_day_gb" in data and isinstance(data["automation_max_total_size_per_day_gb"], (int, float)) and float(data["automation_max_total_size_per_day_gb"]) > 0:
                        self._automation_max_total_size_per_day_gb = float(data["automation_max_total_size_per_day_gb"])
                    if "automation_require_compatible_release" in data and isinstance(data["automation_require_compatible_release"], bool):
                        self._automation_require_compatible_release = data["automation_require_compatible_release"]
                    if "automation_history_retention_days" in data and isinstance(data["automation_history_retention_days"], (int, float)) and 7 <= int(data["automation_history_retention_days"]) <= 90:
                        self._automation_history_retention_days = int(data["automation_history_retention_days"])
                    if "automation_excluded_words" in data and isinstance(data["automation_excluded_words"], list):
                        self._automation_excluded_words = [str(w).strip() for w in data["automation_excluded_words"] if str(w).strip()]
                    if "automation_excluded_regex" in data:
                        r_val = data["automation_excluded_regex"]
                        self._automation_excluded_regex = str(r_val).strip() if r_val and str(r_val).strip() else None
                    if "automation_paused" in data and isinstance(data["automation_paused"], bool):
                        self._automation_paused = data["automation_paused"]
                    if "automation_quality_upgrades_enabled" in data and isinstance(data["automation_quality_upgrades_enabled"], bool):
                        self._automation_quality_upgrades_enabled = data["automation_quality_upgrades_enabled"]
                    if "storage_folders" in data and isinstance(data["storage_folders"], dict):
                        defaults = self._get_default_storage_folders()
                        defaults.update({k: str(v) for k, v in data["storage_folders"].items() if isinstance(v, str)})
                        self._storage_folders = defaults
                    else:
                        self._storage_folders = self._get_default_storage_folders()
                logger.info(
                    f"Loaded runtime settings from {target_file}: retention_enabled={self._retention_enabled}, "
                    f"retention_days={self._retention_days}, media_discovery_enabled={self._media_discovery_enabled}, "
                    f"tmdb_enabled={self._tmdb_enabled}, tmdb_configured={bool(self._tmdb_api_key)}, "
                    f"prowlarr_enabled={self._prowlarr_enabled}, prowlarr_configured={bool(self._prowlarr_api_key)}, "
                    f"monitoring_enabled={self._monitoring_enabled}, monitoring_interval={self._monitoring_interval_hours}h, "
                    f"automation_enabled={self._automation_enabled}"
                )
            except Exception as e:
                logger.warning(f"Could not read settings file {target_file}: {e}. Using defaults.")

        if not self._storage_folders:
            self._storage_folders = self._get_default_storage_folders()

        self._initialized = True

    def get_settings(self) -> Dict[str, Any]:
        """Returns the current settings."""
        self.init_settings()
        api_key_masked = None
        if self._tmdb_api_key:
            k = self._tmdb_api_key
            api_key_masked = ("•" * (len(k) - 4) + k[-4:]) if len(k) >= 4 else "••••"

        prowlarr_key_masked = None
        if self._prowlarr_api_key:
            pk = self._prowlarr_api_key
            prowlarr_key_masked = ("•" * (len(pk) - 4) + pk[-4:]) if len(pk) >= 4 else "••••"

        return {
            "retention_enabled": self._retention_enabled,
            "retention_days": self._retention_days,
            "allowed_retention_days": ALLOWED_RETENTION_DAYS,
            "media_discovery_enabled": self._media_discovery_enabled,
            "tmdb_enabled": self._tmdb_enabled,
            "tmdb_api_key_configured": bool(self._tmdb_api_key and self._tmdb_api_key.strip()),
            "tmdb_api_key_masked": api_key_masked,
            "prowlarr_enabled": self._prowlarr_enabled,
            "prowlarr_url": self._prowlarr_url,
            "prowlarr_api_key_configured": bool(self._prowlarr_api_key and self._prowlarr_api_key.strip()),
            "prowlarr_api_key_masked": prowlarr_key_masked,
            "prowlarr_timeout_seconds": self._prowlarr_timeout_seconds,
            "monitoring_enabled": self._monitoring_enabled,
            "monitoring_interval_hours": self._monitoring_interval_hours,
            "allowed_monitoring_intervals": ALLOWED_MONITORING_INTERVAL_HOURS,
            "monitoring_max_concurrency": self._monitoring_max_concurrency,
            "monitoring_max_targets_per_cycle": self._monitoring_max_targets_per_cycle,
            "monitoring_cooldown_hours": self._monitoring_cooldown_hours,
            "monitoring_history_retention_days": self._monitoring_history_retention_days,
            "monitoring_search_movies": self._monitoring_search_movies,
            "monitoring_search_episodes": self._monitoring_search_episodes,
            # Phase 7A: Automation
            "automation_enabled": self._automation_enabled,
            "automation_dry_run": self._automation_dry_run,
            "automation_min_score": self._automation_min_score,
            "automation_min_seeders": self._automation_min_seeders,
            "automation_max_release_size_gb": self._automation_max_release_size_gb,
            "automation_min_free_space_gb": self._automation_min_free_space_gb,
            "automation_max_downloads_per_cycle": self._automation_max_downloads_per_cycle,
            "automation_max_downloads_per_day": self._automation_max_downloads_per_day,
            "automation_max_concurrent_downloads": self._automation_max_concurrent_downloads,
            "automation_cooldown_hours": self._automation_cooldown_hours,
            "automation_max_total_size_per_cycle_gb": self._automation_max_total_size_per_cycle_gb,
            "automation_max_total_size_per_day_gb": self._automation_max_total_size_per_day_gb,
            "automation_require_compatible_release": self._automation_require_compatible_release,
            "automation_history_retention_days": self._automation_history_retention_days,
            "automation_excluded_words": self._automation_excluded_words,
            "automation_excluded_regex": self._automation_excluded_regex,
            "automation_paused": self._automation_paused,
            "automation_quality_upgrades_enabled": self._automation_quality_upgrades_enabled,
            "storage_folders": self.get_all_storage_folders(),
        }

    def update_settings(
        self,
        retention_enabled: Optional[bool] = None,
        retention_days: Optional[int] = None,
        media_discovery_enabled: Optional[bool] = None,
        tmdb_enabled: Optional[bool] = None,
        tmdb_api_key: Optional[str] = None,
        prowlarr_enabled: Optional[bool] = None,
        prowlarr_url: Optional[str] = None,
        prowlarr_api_key: Optional[str] = None,
        prowlarr_timeout_seconds: Optional[int] = None,
        monitoring_enabled: Optional[bool] = None,
        monitoring_interval_hours: Optional[int] = None,
        monitoring_max_concurrency: Optional[int] = None,
        monitoring_max_targets_per_cycle: Optional[int] = None,
        monitoring_cooldown_hours: Optional[int] = None,
        monitoring_history_retention_days: Optional[int] = None,
        monitoring_search_movies: Optional[bool] = None,
        monitoring_search_episodes: Optional[bool] = None,
        automation_enabled: Optional[bool] = None,
        automation_dry_run: Optional[bool] = None,
        automation_min_score: Optional[int] = None,
        automation_min_seeders: Optional[int] = None,
        automation_max_release_size_gb: Optional[float] = None,
        automation_min_free_space_gb: Optional[float] = None,
        automation_max_downloads_per_cycle: Optional[int] = None,
        automation_max_downloads_per_day: Optional[int] = None,
        automation_max_concurrent_downloads: Optional[int] = None,
        automation_cooldown_hours: Optional[int] = None,
        automation_max_total_size_per_cycle_gb: Optional[float] = None,
        automation_max_total_size_per_day_gb: Optional[float] = None,
        automation_require_compatible_release: Optional[bool] = None,
        automation_history_retention_days: Optional[int] = None,
        automation_excluded_words: Optional[List[str]] = None,
        automation_excluded_regex: Optional[str] = None,
        automation_paused: Optional[bool] = None,
        automation_quality_upgrades_enabled: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Updates runtime settings, validates ranges, and persists changes to disk atomically.
        """
        self.init_settings()

        if retention_days is not None:
            if retention_days not in ALLOWED_RETENTION_DAYS:
                raise ValidationError(
                    f"Invalid retention_days '{retention_days}'. Allowed values: {ALLOWED_RETENTION_DAYS}."
                )
            self._retention_days = retention_days

        if retention_enabled is not None:
            self._retention_enabled = bool(retention_enabled)

        if media_discovery_enabled is not None:
            self._media_discovery_enabled = bool(media_discovery_enabled)

        if tmdb_enabled is not None:
            self._tmdb_enabled = bool(tmdb_enabled)

        if tmdb_api_key is not None:
            clean_key = tmdb_api_key.strip()
            self._tmdb_api_key = clean_key if clean_key else None

        if prowlarr_enabled is not None:
            self._prowlarr_enabled = bool(prowlarr_enabled)

        if prowlarr_url is not None:
            clean_url = prowlarr_url.strip()
            if clean_url:
                from app.services.security import SecurityService
                self._prowlarr_url = SecurityService.validate_prowlarr_url(clean_url)
            else:
                self._prowlarr_url = None

        if prowlarr_api_key is not None:
            clean_pk = prowlarr_api_key.strip()
            self._prowlarr_api_key = clean_pk if clean_pk else None

        if prowlarr_timeout_seconds is not None:
            if not (2 <= prowlarr_timeout_seconds <= 120):
                raise ValidationError("prowlarr_timeout_seconds must be between 2 and 120 seconds.")
            self._prowlarr_timeout_seconds = int(prowlarr_timeout_seconds)

        if monitoring_enabled is not None:
            self._monitoring_enabled = bool(monitoring_enabled)

        if monitoring_interval_hours is not None:
            if monitoring_interval_hours not in ALLOWED_MONITORING_INTERVAL_HOURS:
                raise ValidationError(
                    f"Invalid monitoring_interval_hours '{monitoring_interval_hours}'. Allowed values: {ALLOWED_MONITORING_INTERVAL_HOURS}."
                )
            self._monitoring_interval_hours = int(monitoring_interval_hours)

        if monitoring_max_concurrency is not None:
            if not (1 <= monitoring_max_concurrency <= 5):
                raise ValidationError("monitoring_max_concurrency must be between 1 and 5.")
            self._monitoring_max_concurrency = int(monitoring_max_concurrency)

        if monitoring_max_targets_per_cycle is not None:
            if not (5 <= monitoring_max_targets_per_cycle <= 50):
                raise ValidationError("monitoring_max_targets_per_cycle must be between 5 and 50.")
            self._monitoring_max_targets_per_cycle = int(monitoring_max_targets_per_cycle)

        if monitoring_cooldown_hours is not None:
            if not (1 <= monitoring_cooldown_hours <= 48):
                raise ValidationError("monitoring_cooldown_hours must be between 1 and 48 hours.")
            self._monitoring_cooldown_hours = int(monitoring_cooldown_hours)

        if monitoring_history_retention_days is not None:
            if not (7 <= monitoring_history_retention_days <= 90):
                raise ValidationError("monitoring_history_retention_days must be between 7 and 90 days.")
            self._monitoring_history_retention_days = int(monitoring_history_retention_days)

        if monitoring_search_movies is not None:
            self._monitoring_search_movies = bool(monitoring_search_movies)

        if monitoring_search_episodes is not None:
            self._monitoring_search_episodes = bool(monitoring_search_episodes)

        # Phase 7A: Automation validations
        if automation_enabled is not None:
            self._automation_enabled = bool(automation_enabled)

        if automation_dry_run is not None:
            self._automation_dry_run = bool(automation_dry_run)

        if automation_min_score is not None:
            if not (0 <= automation_min_score <= 1000):
                raise ValidationError("automation_min_score must be between 0 and 1000.")
            self._automation_min_score = int(automation_min_score)

        if automation_min_seeders is not None:
            if automation_min_seeders < 0:
                raise ValidationError("automation_min_seeders must be greater than or equal to 0.")
            self._automation_min_seeders = int(automation_min_seeders)

        if automation_max_release_size_gb is not None:
            if automation_max_release_size_gb <= 0:
                raise ValidationError("automation_max_release_size_gb must be greater than 0.")
            self._automation_max_release_size_gb = float(automation_max_release_size_gb)

        if automation_min_free_space_gb is not None:
            if automation_min_free_space_gb < 0:
                raise ValidationError("automation_min_free_space_gb must be greater than or equal to 0.")
            self._automation_min_free_space_gb = float(automation_min_free_space_gb)

        if automation_max_downloads_per_cycle is not None:
            if not (1 <= automation_max_downloads_per_cycle <= 50):
                raise ValidationError("automation_max_downloads_per_cycle must be between 1 and 50.")
            self._automation_max_downloads_per_cycle = int(automation_max_downloads_per_cycle)

        if automation_max_downloads_per_day is not None:
            if not (1 <= automation_max_downloads_per_day <= 200):
                raise ValidationError("automation_max_downloads_per_day must be between 1 and 200.")
            self._automation_max_downloads_per_day = int(automation_max_downloads_per_day)

        if automation_max_concurrent_downloads is not None:
            if not (1 <= automation_max_concurrent_downloads <= 10):
                raise ValidationError("automation_max_concurrent_downloads must be between 1 and 10.")
            self._automation_max_concurrent_downloads = int(automation_max_concurrent_downloads)

        if automation_cooldown_hours is not None:
            if not (1 <= automation_cooldown_hours <= 48):
                raise ValidationError("automation_cooldown_hours must be between 1 and 48 hours.")
            self._automation_cooldown_hours = int(automation_cooldown_hours)

        if automation_max_total_size_per_cycle_gb is not None:
            if automation_max_total_size_per_cycle_gb <= 0:
                raise ValidationError("automation_max_total_size_per_cycle_gb must be greater than 0.")
            self._automation_max_total_size_per_cycle_gb = float(automation_max_total_size_per_cycle_gb)

        if automation_max_total_size_per_day_gb is not None:
            if automation_max_total_size_per_day_gb <= 0:
                raise ValidationError("automation_max_total_size_per_day_gb must be greater than 0.")
            self._automation_max_total_size_per_day_gb = float(automation_max_total_size_per_day_gb)

        if automation_require_compatible_release is not None:
            self._automation_require_compatible_release = bool(automation_require_compatible_release)

        if automation_history_retention_days is not None:
            if not (7 <= automation_history_retention_days <= 90):
                raise ValidationError("automation_history_retention_days must be between 7 and 90 days.")
            self._automation_history_retention_days = int(automation_history_retention_days)

        if automation_excluded_words is not None:
            self._automation_excluded_words = [str(w).strip() for w in automation_excluded_words if str(w).strip()]

        if automation_excluded_regex is not None:
            clean_rx = automation_excluded_regex.strip()
            if clean_rx:
                try:
                    re.compile(clean_rx)
                except re.error as e:
                    raise ValidationError(f"Invalid automation_excluded_regex: {e}")
                self._automation_excluded_regex = clean_rx
            else:
                self._automation_excluded_regex = None

        if automation_paused is not None:
            self._automation_paused = bool(automation_paused)

        if automation_quality_upgrades_enabled is not None:
            self._automation_quality_upgrades_enabled = bool(automation_quality_upgrades_enabled)

        # Persist to disk atomically
        self._save_settings()
        return self.get_settings()

    def _save_settings(self) -> None:
        storage_path = self._get_storage_path()
        try:
            storage_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_file = storage_path.with_suffix(".tmp")
            payload = {
                "retention_enabled": self._retention_enabled,
                "retention_days": self._retention_days,
                "media_discovery_enabled": self._media_discovery_enabled,
                "tmdb_enabled": self._tmdb_enabled,
                "tmdb_api_key": self._tmdb_api_key or "",
                "prowlarr_enabled": self._prowlarr_enabled,
                "prowlarr_url": self._prowlarr_url or "",
                "prowlarr_api_key": self._prowlarr_api_key or "",
                "prowlarr_timeout_seconds": self._prowlarr_timeout_seconds,
                "monitoring_enabled": self._monitoring_enabled,
                "monitoring_interval_hours": self._monitoring_interval_hours,
                "monitoring_max_concurrency": self._monitoring_max_concurrency,
                "monitoring_max_targets_per_cycle": self._monitoring_max_targets_per_cycle,
                "monitoring_cooldown_hours": self._monitoring_cooldown_hours,
                "monitoring_history_retention_days": self._monitoring_history_retention_days,
                "monitoring_search_movies": self._monitoring_search_movies,
                "monitoring_search_episodes": self._monitoring_search_episodes,
                # Phase 7A: Automation
                "automation_enabled": self._automation_enabled,
                "automation_dry_run": self._automation_dry_run,
                "automation_min_score": self._automation_min_score,
                "automation_min_seeders": self._automation_min_seeders,
                "automation_max_release_size_gb": self._automation_max_release_size_gb,
                "automation_min_free_space_gb": self._automation_min_free_space_gb,
                "automation_max_downloads_per_cycle": self._automation_max_downloads_per_cycle,
                "automation_max_downloads_per_day": self._automation_max_downloads_per_day,
                "automation_max_concurrent_downloads": self._automation_max_concurrent_downloads,
                "automation_cooldown_hours": self._automation_cooldown_hours,
                "automation_max_total_size_per_cycle_gb": self._automation_max_total_size_per_cycle_gb,
                "automation_max_total_size_per_day_gb": self._automation_max_total_size_per_day_gb,
                "automation_require_compatible_release": self._automation_require_compatible_release,
                "automation_history_retention_days": self._automation_history_retention_days,
                "automation_excluded_words": self._automation_excluded_words,
                "automation_excluded_regex": self._automation_excluded_regex,
                "automation_paused": self._automation_paused,
                "automation_quality_upgrades_enabled": self._automation_quality_upgrades_enabled,
                "storage_folders": self.get_all_storage_folders(),
            }
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            os.replace(str(tmp_file), str(storage_path))
            log_payload = {k: v for k, v in payload.items() if k not in ("tmdb_api_key", "prowlarr_api_key")}
            log_payload["tmdb_api_key"] = "configured" if self._tmdb_api_key else "empty"
            log_payload["prowlarr_api_key"] = "configured" if self._prowlarr_api_key else "empty"
            logger.info(f"Persisted settings to {storage_path}: {log_payload}")
        except Exception as e:
            logger.error(f"Failed to persist settings to {storage_path}: {e}")

    @property
    def retention_enabled(self) -> bool:
        self.init_settings()
        return self._retention_enabled

    @property
    def retention_days(self) -> int:
        self.init_settings()
        return self._retention_days

    @property
    def retention_seconds(self) -> int:
        if not self.retention_enabled:
            return 0
        return self.retention_days * 86400

    @property
    def media_discovery_enabled(self) -> bool:
        self.init_settings()
        return self._media_discovery_enabled

    @property
    def tmdb_enabled(self) -> bool:
        self.init_settings()
        return self._tmdb_enabled

    @property
    def tmdb_api_key(self) -> Optional[str]:
        self.init_settings()
        return self._tmdb_api_key

    @property
    def prowlarr_enabled(self) -> bool:
        self.init_settings()
        return self._prowlarr_enabled

    @property
    def prowlarr_url(self) -> Optional[str]:
        self.init_settings()
        return self._prowlarr_url

    @property
    def prowlarr_api_key(self) -> Optional[str]:
        self.init_settings()
        return self._prowlarr_api_key

    @property
    def prowlarr_timeout_seconds(self) -> int:
        self.init_settings()
        return self._prowlarr_timeout_seconds

    @property
    def monitoring_enabled(self) -> bool:
        self.init_settings()
        return self._monitoring_enabled

    @property
    def monitoring_interval_hours(self) -> int:
        self.init_settings()
        return self._monitoring_interval_hours

    @property
    def monitoring_max_concurrency(self) -> int:
        self.init_settings()
        return self._monitoring_max_concurrency

    @property
    def monitoring_max_targets_per_cycle(self) -> int:
        self.init_settings()
        return self._monitoring_max_targets_per_cycle

    @property
    def monitoring_cooldown_hours(self) -> int:
        self.init_settings()
        return self._monitoring_cooldown_hours

    @property
    def monitoring_history_retention_days(self) -> int:
        self.init_settings()
        return self._monitoring_history_retention_days

    @property
    def monitoring_search_movies(self) -> bool:
        self.init_settings()
        return self._monitoring_search_movies

    @property
    def monitoring_search_episodes(self) -> bool:
        self.init_settings()
        return self._monitoring_search_episodes

    # Phase 7A: Automation Properties
    @property
    def automation_enabled(self) -> bool:
        self.init_settings()
        return self._automation_enabled

    @property
    def automation_dry_run(self) -> bool:
        self.init_settings()
        return self._automation_dry_run

    @property
    def automation_min_score(self) -> int:
        self.init_settings()
        return self._automation_min_score

    @property
    def automation_min_seeders(self) -> int:
        self.init_settings()
        return self._automation_min_seeders

    @property
    def automation_max_release_size_gb(self) -> float:
        self.init_settings()
        return self._automation_max_release_size_gb

    @property
    def automation_min_free_space_gb(self) -> float:
        self.init_settings()
        return self._automation_min_free_space_gb

    @property
    def automation_max_downloads_per_cycle(self) -> int:
        self.init_settings()
        return self._automation_max_downloads_per_cycle

    @property
    def automation_max_downloads_per_day(self) -> int:
        self.init_settings()
        return self._automation_max_downloads_per_day

    @property
    def automation_max_concurrent_downloads(self) -> int:
        self.init_settings()
        return self._automation_max_concurrent_downloads

    @property
    def automation_cooldown_hours(self) -> int:
        self.init_settings()
        return self._automation_cooldown_hours

    @property
    def automation_max_total_size_per_cycle_gb(self) -> float:
        self.init_settings()
        return self._automation_max_total_size_per_cycle_gb

    @property
    def automation_max_total_size_per_day_gb(self) -> float:
        self.init_settings()
        return self._automation_max_total_size_per_day_gb

    @property
    def automation_require_compatible_release(self) -> bool:
        self.init_settings()
        return self._automation_require_compatible_release

    @property
    def automation_history_retention_days(self) -> int:
        self.init_settings()
        return self._automation_history_retention_days

    @property
    def automation_excluded_words(self) -> List[str]:
        self.init_settings()
        return self._automation_excluded_words

    @property
    def automation_excluded_regex(self) -> Optional[str]:
        self.init_settings()
        return self._automation_excluded_regex

    @property
    def automation_paused(self) -> bool:
        self.init_settings()
        return self._automation_paused

    @property
    def automation_quality_upgrades_enabled(self) -> bool:
        self.init_settings()
        return self._automation_quality_upgrades_enabled

    def get_storage_folder(self, category: str) -> Optional[str]:
        if not self._initialized or not self._storage_folders:
            self.init_settings()
        return self._storage_folders.get(category)

    def set_storage_folder(self, category: str, path_str: str) -> Dict[str, str]:
        if not self._initialized or not self._storage_folders:
            self.init_settings()
        self._storage_folders[category] = str(path_str)
        self._save_settings()
        return dict(self._storage_folders)

    def set_all_storage_folders(self, folders: Dict[str, str]) -> Dict[str, str]:
        if not self._initialized or not self._storage_folders:
            self.init_settings()
        for k, v in folders.items():
            if isinstance(v, str):
                self._storage_folders[k] = v
        self._save_settings()
        return dict(self._storage_folders)

    def get_all_storage_folders(self) -> Dict[str, str]:
        if not self._initialized or not self._storage_folders:
            self.init_settings()
        return dict(self._storage_folders)


settings_service = SettingsService()
