from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    ANALYZING = "ANALYZING"
    WAITING_FOR_METADATA = "WAITING_FOR_METADATA"
    ACQUIRING_METADATA = "ACQUIRING_METADATA"
    READY = "READY"
    WAITING_FOR_SELECTION = "WAITING_FOR_SELECTION"
    DOWNLOADING = "DOWNLOADING"
    PROCESSING = "PROCESSING"
    SEEDING = "SEEDING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    METADATA_FAILED = "METADATA_FAILED"
    CANCELLED = "CANCELLED"
    INTERRUPTED = "INTERRUPTED"


class VideoQualityOption(BaseModel):
    label: str               # e.g., "1080p (Full HD)"
    resolution: str          # e.g., "1080p", "720p", "best"
    height: Optional[int] = None
    width: Optional[int] = None
    fps: Optional[int] = None
    vcodec: Optional[str] = None
    acodec: Optional[str] = None
    filesize_approx: Optional[str] = None
    tbr: Optional[float] = None
    ext: str = "mp4"


class AudioQualityOption(BaseModel):
    label: str               # e.g., "MP3 (Best Audio, 320 kbps)"
    format: str              # e.g., "mp3", "m4a", "wav", "flac", "opus"
    ext: str = "mp3"
    bitrate: Optional[str] = "320k"


class TechnicalSummary(BaseModel):
    resolution_str: Optional[str] = None
    fps: Optional[int] = None
    vcodec: Optional[str] = None
    acodec: Optional[str] = None
    tbr: Optional[float] = None
    format_count: int = 0
    media_type: str = "video"


class PlaylistItem(BaseModel):
    id: str
    title: str
    duration: Optional[int] = None
    duration_string: Optional[str] = None
    uploader: Optional[str] = None
    thumbnail: Optional[str] = None
    url: str
    index: int = 1


class TorrentFileItem(BaseModel):
    index: int = 0
    path: str
    size: int
    size_formatted: Optional[str] = None
    selected: bool = True
    priority: str = "normal"  # high, normal, low, skip


class TorrentMetadataResponse(BaseModel):
    info_hash: str
    name: str
    total_size: int
    total_size_formatted: str
    file_count: int
    piece_count: int = 0
    piece_length: int = 0
    trackers: List[str] = []
    created_date: Optional[str] = None
    comment: Optional[str] = None
    is_multi_file: bool = False
    files: List[TorrentFileItem] = []
    has_metadata: bool = True
    magnet_uri: Optional[str] = None


class TorrentDownloadConfig(BaseModel):
    info_hash: str
    name: Optional[str] = None
    selected_indices: Optional[List[int]] = None
    selected_files: Optional[List[int]] = None
    file_priorities: Optional[Dict[int, str]] = None
    destination_folder: Optional[str] = None
    seeding_mode: str = "stop"  # stop, ratio_1, ratio_2, time_30m, time_2h, indefinite
    torrent_file_path: Optional[str] = None
    magnet_uri: Optional[str] = None
    manual_review: bool = False
    interactive: bool = False


class TorrentTelemetry(BaseModel):
    info_hash: str
    name: str
    state: Optional[str] = "downloading"
    total_size: int
    total_size_formatted: str
    downloaded_bytes: int
    uploaded_bytes: int
    download_speed: str
    upload_speed: str
    ratio: float
    peers: int
    seeds: int
    leeches: int
    eta: Optional[str] = None
    seeding_mode: str = "stop"
    is_seeding: bool = False
    file_count: int = 0
    files: List[Dict[str, Any]] = []
    trackers_contacted: int = 0
    dht_active: bool = False
    metadata_phase: Optional[str] = None
    metadata_retry_count: int = 0
    next_retry_in: Optional[int] = None
    cached: bool = False


class AnalyzeRequest(BaseModel):
    url: str = Field(..., description="The media URL to analyze")


class AnalyzeResponse(BaseModel):
    url: str
    title: str
    thumbnail: Optional[str] = None
    duration: Optional[int] = None
    duration_string: Optional[str] = None
    uploader: Optional[str] = None
    uploader_avatar: Optional[str] = None
    upload_date: Optional[str] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    webpage_url: str
    extractor: str
    media_type: str = "video"
    video_available: bool = True
    audio_available: bool = True
    video_options: List[VideoQualityOption] = []
    audio_options: List[AudioQualityOption] = []
    supported_containers: List[str] = ["mp4", "mkv", "webm"]
    technical_summary: Optional[TechnicalSummary] = None
    is_playlist: bool = False
    playlist_id: Optional[str] = None
    entry_count: Optional[int] = None
    entries: List[PlaylistItem] = []
    provider: str = "ytdlp"
    is_torrent: bool = False
    torrent_info: Optional[TorrentMetadataResponse] = None


class TorrentAnalysisResponse(BaseModel):
    type: str = "torrent"
    input_type: str = "magnet"
    status: str = "ready"  # metadata_pending | ready | failed
    info_hash: str
    name: Optional[str] = None
    total_size: Optional[int] = None
    total_size_formatted: Optional[str] = None
    file_count: int = 0
    files: List[TorrentFileItem] = []
    trackers: List[str] = []
    magnet_uri: Optional[str] = None
    # Compatibility properties for UI components
    url: Optional[str] = None
    title: Optional[str] = None
    torrent_info: Optional[TorrentMetadataResponse] = None
    extractor: str = "torrent:magnet"
    media_type: str = "torrent"
    is_torrent: bool = True
    provider: str = "torrent"
    job_id: Optional[str] = None



class DownloadConfig(BaseModel):
    preset: str = Field(default="recommended", description="Preset name: recommended, best_quality, audio_only, small_file, archive, custom")
    quality: str = Field(default="best", description="Resolution: best, 2160p, 1440p, 1080p, 720p, 480p, 360p")
    output_container: str = Field(default="mp4", description="Output container: mp4, mkv, webm, mp3, m4a, wav, flac, opus")
    audio_mode: str = Field(default="merge", description="merge (video+audio) or audio_only")
    audio_format: str = Field(default="mp3", description="Audio format: mp3, m4a, wav, flac, opus")
    audio_quality: str = Field(default="0", description="Audio quality (0 = best, or bitrate like 320k)")
    video_codec: str = Field(default="any", description="Video codec preference: any, h264, vp9, av1")
    filename_template: str = Field(default="%(title).150B.%(ext)s", description="Safe filename output template")
    subtitles: bool = Field(default=False, description="Download subtitles if available")
    embed_subtitles: bool = Field(default=False, description="Embed subtitles into output container")
    auto_subtitles: bool = Field(default=False, description="Include automatic subtitles")
    subtitle_langs: str = Field(default="en", description="Subtitle languages (e.g. en, all)")
    embed_metadata: bool = Field(default=True, description="Embed metadata into container")
    embed_thumbnail: bool = Field(default=True, description="Embed thumbnail as cover art")
    write_chapters: bool = Field(default=False, description="Embed chapters")
    retries: int = Field(default=10, ge=1, le=100, description="Network retry attempts")
    timeout: int = Field(default=30, ge=5, le=3600, description="Socket request timeout in seconds")
    concurrent_fragments: int = Field(default=1, ge=1, le=16, description="Concurrent download fragments")
    playlist_mode: str = Field(default="single", description="single, all, selected, range, or playlist")
    playlist_items: Optional[str] = Field(default=None, description="Playlist items range (e.g. 1-10 or 1,3,5)")
    playlist_start: Optional[int] = Field(default=None, description="Playlist start index (1-based)")
    playlist_end: Optional[int] = Field(default=None, description="Playlist end index (1-based)")
    selected_indices: Optional[List[int]] = Field(default=None, description="Specific playlist item indices to download")


class PresetDefinition(BaseModel):
    id: str
    name: str
    description: str
    badge: Optional[str] = None
    config: DownloadConfig


class PresetsResponse(BaseModel):
    presets: List[PresetDefinition]
    default_preset: str = "recommended"


class JobPriority(str, Enum):
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


class DownloadRequest(BaseModel):
    url: str = Field(..., description="Target media URL")
    title: Optional[str] = None
    config: Optional[DownloadConfig] = None
    priority: Optional[str] = Field(default="NORMAL", description="Queue priority: HIGH, NORMAL, LOW")
    profile_id: Optional[str] = Field(default=None, description="Profile ID to use for download")
    scheduled_for: Optional[float] = Field(default=None, description="Timestamp for scheduled execution")
    schedule_type: Optional[str] = Field(default="once", description="Schedule type: once, daily, weekly")
    bandwidth_limit: Optional[int] = Field(default=0, description="Rate limit in bytes per second (0 = unlimited)")
    # Torrent integration
    provider: str = Field(default="ytdlp", description="Download provider: ytdlp or torrent")
    input_type: Optional[str] = Field(default=None, description="Input type: url, magnet, or torrent_file")
    override_duplicate: bool = Field(default=False, description="Force download even if duplicate detected")
    interactive: bool = Field(default=False, description="If True, interactive mode acquires metadata first and pauses payload downloading until user confirms file selection")
    movie_id: Optional[str] = Field(default=None, description="Associated movie ID if initiated from Movie Manager")
    episode_id: Optional[str] = Field(default=None, description="Associated episode ID if initiated from Series Manager")
    job_type: Optional[str] = Field(default="NORMAL", description="Job type: NORMAL or QUALITY_UPGRADE")
    is_upgrade: Optional[bool] = Field(default=False, description="True if this job is an upgrade")
    previous_quality: Optional[str] = Field(default=None, description="Current media quality summary before upgrade")
    upgrade_reason: Optional[str] = Field(default=None, description="Reason / quality delta explaining why this upgrade was selected")
    torrent_config: Optional[TorrentDownloadConfig] = None
    # Legacy fields for backward compatibility
    resolution: Optional[str] = Field(default=None, description="Legacy resolution: best, 1080p, etc.")
    audio_only: Optional[bool] = Field(default=None, description="Legacy audio only toggle")
    audio_format: Optional[str] = Field(default=None, description="Legacy audio format")
    output_container: Optional[str] = Field(default=None, description="Legacy output container")

    def get_resolved_config(self) -> DownloadConfig:
        """Returns structured DownloadConfig, merging legacy fields if provided."""
        if self.config:
            return self.config

        # Map legacy fields into structured config
        audio_mode = "audio_only" if self.audio_only else "merge"
        quality = self.resolution or "best"
        audio_fmt = self.audio_format or "mp3"
        container = (audio_fmt if self.audio_only else (self.output_container or "mp4")).lower()

        return DownloadConfig(
            preset="recommended",
            quality=quality,
            output_container=container,
            audio_mode=audio_mode,
            audio_format=audio_fmt,
        )


class PlaylistFileItem(BaseModel):
    index: int
    filename: str
    filesize: Optional[int] = None
    filesize_formatted: Optional[str] = None
    download_url: str


class DownloadResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str = "Download job queued successfully."
    file_id: Optional[str] = None
    download_url: Optional[str] = None
    provider: Optional[str] = None


class JobResponse(BaseModel):
    id: str
    url: str
    title: Optional[str] = None
    thumbnail: Optional[str] = None
    status: JobStatus
    progress: float = 0.0
    speed: Optional[str] = None
    eta: Optional[str] = None
    current_stage: str = "Queued"
    downloaded_bytes: int = 0
    total_bytes: Optional[int] = None
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    output_filename: Optional[str] = None
    output_filesize: Optional[int] = None
    output_filesize_formatted: Optional[str] = None
    error_message: Optional[str] = None
    file_id: Optional[str] = None
    download_url: Optional[str] = None
    config_summary: Optional[str] = None
    is_playlist: bool = False
    playlist_title: Optional[str] = None
    total_items: int = 0
    completed_items: int = 0
    failed_items: int = 0
    skipped_items: int = 0
    current_item_index: int = 0
    current_item_title: Optional[str] = None
    current_item_progress: float = 0.0
    is_file_available: bool = True
    playlist_files: List[PlaylistFileItem] = []
    priority: str = "NORMAL"
    queue_order: int = 0
    retry_count: int = 0
    max_retries: int = 3
    next_retry_at: Optional[float] = None
    scheduled_for: Optional[float] = None
    schedule_type: str = "once"
    bandwidth_limit: int = 0
    profile_id: Optional[str] = "recommended"
    # Torrent integration
    provider: str = "ytdlp"
    input_type: str = "url"
    info_hash: Optional[str] = None
    torrent_id: Optional[str] = None
    torrent_telemetry: Optional[TorrentTelemetry] = None
    output_type: Optional[str] = "file"
    file_count: Optional[int] = 1
    torrent_info: Optional[TorrentMetadataResponse] = None
    interactive: bool = False
    movie_id: Optional[str] = None
    episode_id: Optional[str] = None
    job_type: Optional[str] = "NORMAL"
    is_upgrade: Optional[bool] = False
    previous_quality: Optional[str] = None
    upgrade_reason: Optional[str] = None


class JobListResponse(BaseModel):
    jobs: List[JobResponse]
    total: int
    active_count: int


class CancelResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str


class SettingsUpdateRequest(BaseModel):
    retention_enabled: Optional[bool] = None
    retention_days: Optional[int] = None
    download_retention_days: Optional[int] = None
    temp_retention_minutes: Optional[int] = None
    max_concurrent_downloads: Optional[int] = None
    rate_limit: Optional[str] = None
    download_path: Optional[str] = None
    temp_path: Optional[str] = None
    media_discovery_enabled: Optional[bool] = None
    tmdb_enabled: Optional[bool] = None
    tmdb_api_key: Optional[str] = None
    prowlarr_enabled: Optional[bool] = None
    prowlarr_url: Optional[str] = None
    prowlarr_api_key: Optional[str] = None
    prowlarr_timeout_seconds: Optional[int] = None


class SettingsResponse(BaseModel):
    retention_enabled: bool
    retention_days: int
    allowed_retention_days: List[int] = [7, 14, 21, 30]
    global_bandwidth_limit: int = 0
    max_concurrent_downloads: int = 2
    media_discovery_enabled: bool = False
    tmdb_enabled: bool = False
    tmdb_api_key_configured: bool = False
    tmdb_api_key_masked: Optional[str] = None
    prowlarr_enabled: bool = False
    prowlarr_url: Optional[str] = None
    prowlarr_api_key_configured: bool = False
    prowlarr_api_key_masked: Optional[str] = None
    prowlarr_timeout_seconds: int = 60


class SystemInfoResponse(BaseModel):
    app_name: str
    app_version: str
    ytdlp_version: str
    latest_ytdlp_version: Optional[str] = None
    update_available: bool = False
    ffmpeg_available: bool = False
    ffmpeg_version: Optional[str] = None
    active_jobs: int = 0
    max_concurrent_downloads: int = 2
    download_retention: int = 86400
    temp_retention: int = 3600
    max_download_size: str = "10G"
    storage_info: Optional[Dict[str, Any]] = None
    torrent_enabled: bool = True
    torrent_engine: str = "libtorrent"
    torrent_engine_status: str = "healthy"
    torrent_version: Optional[str] = None
    active_torrents: int = 0


class StorageTargetModel(BaseModel):
    name: str
    path: str
    target_type: str
    required: bool
    exists: bool
    is_directory: bool
    readable: bool
    writable: bool
    read_only: bool
    total_bytes: int
    used_bytes: int
    free_bytes: int
    status: str
    error_code: Optional[str] = None
    message: Optional[str] = None
    filesystem: Optional[str] = None


class StorageStatusResponse(BaseModel):
    is_healthy: bool
    required_storage_healthy: bool
    container_identity: Dict[str, Any]
    targets: List[StorageTargetModel]
    issues: List[Dict[str, Any]]
    recommended_compose: str
    locations: Optional[Dict[str, Any]] = None
    folders: Optional[Dict[str, Any]] = None
    media: Optional[Dict[str, Any]] = None


# --- User-Level Storage Folder Schemas ---

class StorageLocationInfo(BaseModel):
    id: str
    name: str
    description: str
    path: str
    exists: bool
    writable: bool
    read_only: bool
    total_bytes: int
    free_bytes: int
    used_bytes: int
    free_formatted: str
    total_formatted: str
    error: Optional[str] = None


class StorageFolderCreateRequest(BaseModel):
    storage_id: str = Field(..., description="Approved storage location ID (e.g. data, media)")
    relative_path: str = Field(default="", description="Relative path within storage location")
    folder_name: str = Field(..., min_length=1, max_length=120, description="Folder name to create")


class StorageFolderSelectRequest(BaseModel):
    category: str = Field(..., description="Folder category: downloads, library, torrents, import, or temp")
    storage_id: str = Field(..., description="Approved storage location ID")
    relative_path: str = Field(default="", description="Relative path within storage location")


class StorageSetupRecommendedRequest(BaseModel):
    storage_id: str = Field(..., description="Approved storage location ID")
    relative_path: str = Field(default="", description="Base relative path for standard folder structure")


class StorageFolderTestRequest(BaseModel):
    storage_id: str = Field(..., description="Approved storage location ID")
    relative_path: str = Field(default="", description="Relative path within storage location")



# --- Batch URL Import ---

class BatchImportRequest(BaseModel):
    urls: List[str] = Field(..., description="List of URLs to download")
    priority: str = Field(default="NORMAL", description="Priority for queued jobs")
    profile_id: Optional[str] = Field(default=None, description="Profile ID to apply")
    folder_template: Optional[str] = Field(default=None, description="Custom folder template")


class BatchItemResult(BaseModel):
    url: str
    valid: bool
    title: Optional[str] = None
    job_id: Optional[str] = None
    duplicate: bool = False
    error: Optional[str] = None


class BatchImportResponse(BaseModel):
    total_submitted: int
    total_accepted: int
    duplicates_skipped: int
    invalid_urls: int
    items: List[BatchItemResult]


# --- Media Library ---

class MediaItem(BaseModel):
    id: str
    job_id: Optional[str] = None
    title: str
    filename: str
    relative_path: str
    source_url: str
    extractor: Optional[str] = None
    media_id: Optional[str] = None
    uploader: Optional[str] = None
    playlist_name: Optional[str] = None
    duration: Optional[int] = None
    duration_string: Optional[str] = None
    resolution: Optional[str] = None
    container: Optional[str] = None
    filesize: Optional[int] = None
    filesize_formatted: Optional[str] = None
    thumbnail_url: Optional[str] = None
    is_favorite: bool = False
    is_protected: bool = False
    created_at: float
    downloaded_at: float
    stream_url: str
    download_url: str
    source_provider: str = "ytdlp"
    torrent_id: Optional[str] = None


class MediaListResponse(BaseModel):
    items: List[MediaItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class MediaStorageSummary(BaseModel):
    total_files: int
    total_bytes: int
    total_formatted: str
    videos_count: int
    videos_bytes: int
    audio_count: int
    audio_bytes: int
    playlists_count: int
    playlists_bytes: int
    disk_free_bytes: int
    disk_total_bytes: int
    disk_free_formatted: str


# --- Profiles ---

class ProfileModel(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    badge: Optional[str] = None
    is_builtin: bool = False
    is_default: bool = False
    config: DownloadConfig
    created_at: float
    updated_at: float


class ProfileCreateRequest(BaseModel):
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    badge: Optional[str] = None
    config: DownloadConfig


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    badge: Optional[str] = None
    config: Optional[DownloadConfig] = None
    is_default: Optional[bool] = None


# --- Rules ---

class RuleModel(BaseModel):
    id: str
    name: str
    condition_type: str  # domain, extractor, title_regex, is_playlist, is_audio
    condition_value: str
    profile_id: str
    priority: int = 0
    is_enabled: bool = True
    created_at: float


class RuleCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    condition_type: str = Field(..., description="domain, extractor, title_regex, is_playlist")
    condition_value: str = Field(..., description="Condition pattern to match")
    profile_id: str = Field(..., description="Profile ID to apply when matched")
    priority: int = Field(default=0, description="Higher number evaluates first")
    is_enabled: bool = Field(default=True)


class RuleUpdateRequest(BaseModel):
    name: Optional[str] = None
    condition_type: Optional[str] = None
    condition_value: Optional[str] = None
    profile_id: Optional[str] = None
    priority: Optional[int] = None
    is_enabled: Optional[bool] = None


class RuleMatchResult(BaseModel):
    matched: bool
    rule_name: Optional[str] = None
    profile_id: Optional[str] = None
    profile_name: Optional[str] = None
    reason: Optional[str] = None


# --- API Keys ---

class ApiKeyModel(BaseModel):
    id: str
    name: str
    key_prefix: str
    created_at: float
    last_used_at: Optional[float] = None
    is_active: bool = True


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)


class ApiKeyCreateResponse(BaseModel):
    id: str
    name: str
    api_key: str
    key_prefix: str
    message: str = "Store this API key safely. It will never be displayed again."


# --- Webhooks ---

class WebhookModel(BaseModel):
    id: str
    url: str
    events: List[str]
    signing_secret: Optional[str] = None
    is_enabled: bool = True
    created_at: float


class WebhookCreateRequest(BaseModel):
    url: str = Field(..., description="HTTP/HTTPS endpoint")
    events: List[str] = Field(..., description="List of events: job.started, job.completed, job.failed, batch.completed")
    signing_secret: Optional[str] = Field(default=None, description="Optional secret for HMAC-SHA256 signature")


class WebhookDeliveryModel(BaseModel):
    id: str
    webhook_id: str
    event: str
    payload_summary: Optional[str] = None
    status_code: Optional[int] = None
    success: bool
    attempt_count: int
    error_message: Optional[str] = None
    delivered_at: float


# --- Queue Controls ---

class QueueReorderRequest(BaseModel):
    job_ids: List[str] = Field(..., description="Ordered list of pending job IDs")


class QueuePriorityRequest(BaseModel):
    priority: str = Field(..., description="HIGH, NORMAL, or LOW")


class ScheduleDownloadRequest(BaseModel):
    scheduled_for: float = Field(..., description="Unix timestamp for execution")
    schedule_type: str = Field(default="once", description="once, daily, or weekly")


# --- Statistics ---

class StatisticsResponse(BaseModel):
    total_downloads: int
    completed_downloads: int
    failed_downloads: int
    cancelled_downloads: int
    total_bytes_downloaded: int
    total_formatted: str
    active_downloads: int
    queued_downloads: int
    top_extractors: List[Dict[str, Any]]
    top_containers: List[Dict[str, Any]]
    downloads_by_day: List[Dict[str, Any]]



# =====================================================================
# Phase 2: Watchers, Recipes, Preflight, Quality Upgrades & Media Health
# =====================================================================

# --- Watchers ---

class WatcherCreateRequest(BaseModel):
    name: str = Field(..., description="Human-readable collection/channel title")
    source_url: str = Field(..., description="Supported playlist, channel, or collection URL")
    source_type: str = Field(default="playlist", description="playlist, channel, feed, or collection")
    schedule: str = Field(default="every_6_hours", description="hourly, every_3_hours, every_6_hours, every_12_hours, daily, weekly, custom")
    interval_seconds: Optional[int] = Field(default=None, description="Interval in seconds if custom")
    profile_id: str = Field(default="recommended", description="Target profile ID")
    recipe_id: Optional[str] = Field(default=None, description="Optional recipe ID")
    target_quality: str = Field(default="1080p", description="1080p, best, 720p, etc.")
    minimum_quality: str = Field(default="720p", description="Minimum acceptable quality")
    upgrade_policy: str = Field(default="ask", description="ask, automatic, never")
    duplicate_policy: str = Field(default="skip", description="skip, overwrite, prompt")
    destination_rule: Optional[str] = Field(default=None, description="Optional destination folder template")
    download_new: bool = Field(default=True, description="Automatically queue new discovered items")
    notify_new: bool = Field(default=True, description="Notify when new items are found")
    notify_completed: bool = Field(default=True, description="Notify when sync completes")
    notify_failed: bool = Field(default=True, description="Notify if sync fails")


class WatcherUpdateRequest(BaseModel):
    name: Optional[str] = None
    schedule: Optional[str] = None
    interval_seconds: Optional[int] = None
    profile_id: Optional[str] = None
    recipe_id: Optional[str] = None
    target_quality: Optional[str] = None
    minimum_quality: Optional[str] = None
    upgrade_policy: Optional[str] = None
    duplicate_policy: Optional[str] = None
    destination_rule: Optional[str] = None
    download_new: Optional[bool] = None
    notify_new: Optional[bool] = None
    notify_completed: Optional[bool] = None
    notify_failed: Optional[bool] = None


class WatcherRunModel(BaseModel):
    id: str
    watcher_id: str
    started_at: float
    completed_at: Optional[float] = None
    status: str
    items_seen: int = 0
    new_items: int = 0
    duplicates: int = 0
    upgrades: int = 0
    queued: int = 0
    failed: int = 0
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class WatcherModel(BaseModel):
    id: str
    name: str
    source_url: str
    source_type: str
    schedule: str
    interval_seconds: int
    status: str
    profile_id: str
    recipe_id: Optional[str] = None
    target_quality: str
    minimum_quality: str
    upgrade_policy: str
    duplicate_policy: str
    destination_rule: Optional[str] = None
    download_new: bool
    notify_new: bool
    notify_completed: bool
    notify_failed: bool
    items_tracked: int
    items_downloaded: int
    last_checked: Optional[float] = None
    next_check: Optional[float] = None
    last_sync_result: Optional[str] = None
    consecutive_failures: int = 0
    last_error: Optional[str] = None
    created_at: float
    updated_at: float
    recent_runs: List[WatcherRunModel] = []


# --- Recipes ---

class RecipeCreateRequest(BaseModel):
    name: str = Field(..., description="Descriptive recipe name")
    description: Optional[str] = None
    profile_id: str = Field(..., description="Base profile ID")
    storage_folder: Optional[str] = Field(default=None, description="Path template (e.g. Archive/{creator}/{title})")
    duplicate_policy: str = Field(default="skip", description="skip or overwrite")
    target_quality: str = Field(default="best", description="Target quality")
    minimum_quality: str = Field(default="720p", description="Minimum quality")
    upgrade_policy: str = Field(default="ask", description="ask, automatic, or never")
    retention_days: int = Field(default=0, description="0 = forever, or 7, 14, 21, 30")
    notify_events: List[str] = Field(default=["job.completed", "job.failed"])


class RecipeUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    profile_id: Optional[str] = None
    storage_folder: Optional[str] = None
    duplicate_policy: Optional[str] = None
    target_quality: Optional[str] = None
    minimum_quality: Optional[str] = None
    upgrade_policy: Optional[str] = None
    retention_days: Optional[int] = None
    notify_events: Optional[List[str]] = None


class RecipeModel(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    profile_id: str
    storage_folder: Optional[str] = None
    duplicate_policy: str = "skip"
    target_quality: str = "best"
    minimum_quality: str = "720p"
    upgrade_policy: str = "ask"
    retention_days: int = 0
    notify_events: List[str] = []
    is_builtin: bool = False
    is_default: bool = False
    created_at: float
    updated_at: float


# --- Preflight ---

class PreflightRequest(BaseModel):
    url: str = Field(..., description="Target media, playlist, or collection URL")
    profile_id: Optional[str] = None
    recipe_id: Optional[str] = None
    selected_indices: Optional[List[int]] = None
    dry_run: bool = Field(default=False, description="Analyze without committing to queue")


class PreflightItemDetail(BaseModel):
    index: int
    title: str
    url: str
    media_id: Optional[str] = None
    status: str = "new"  # new, existing, upgrade, unavailable
    reason: Optional[str] = None
    estimated_bytes: Optional[int] = None
    estimated_bytes_formatted: Optional[str] = None
    current_library_id: Optional[str] = None
    current_resolution: Optional[str] = None
    available_resolution: Optional[str] = None


class PreflightResponse(BaseModel):
    title: str
    is_playlist: bool
    total_items: int
    selected_items: int
    new_items_count: int
    existing_items_count: int
    upgrade_items_count: int
    unavailable_items_count: int
    estimated_total_bytes: Optional[int] = None
    estimated_total_formatted: str
    disk_free_bytes: int
    disk_free_formatted: str
    storage_status: str  # sufficient, warning, critical
    storage_message: str
    resolved_profile_id: str
    resolved_profile_name: str
    resolved_recipe_id: Optional[str] = None
    resolved_recipe_name: Optional[str] = None
    destination_folder: str
    items: List[PreflightItemDetail] = []
    explanations: List[str] = []


# --- Quality Upgrades ---

class QualityTargetModel(BaseModel):
    id: str
    media_id: str
    current_height: Optional[int] = None
    current_fps: Optional[int] = None
    current_filesize: Optional[int] = None
    target_quality: str
    minimum_quality: str
    upgrade_policy: str
    upgrade_available: bool = False
    upgrade_height: Optional[int] = None
    upgrade_filesize: Optional[int] = None
    upgrade_source_url: Optional[str] = None
    status: str
    updated_at: float


class QualityUpgradeActionRequest(BaseModel):
    media_id: str
    action: str = Field(..., description="approve, reject, or ignore")


# --- Media Health ---

class HealthIssueModel(BaseModel):
    id: str
    scan_id: str
    issue_type: str  # missing_file, orphaned_record, duplicate_media, duplicate_file, incomplete_download, invalid_metadata
    severity: str    # info, warning, critical
    media_id: Optional[str] = None
    file_path: Optional[str] = None
    title: Optional[str] = None
    description: str
    details: Optional[Dict[str, Any]] = None
    recommended_action: str
    recoverable_bytes: int = 0
    is_resolved: bool = False
    resolved_at: Optional[float] = None
    resolution_action: Optional[str] = None
    created_at: float


class HealthScanModel(BaseModel):
    id: str
    started_at: float
    completed_at: Optional[float] = None
    status: str
    files_scanned: int = 0
    issues_found: int = 0
    issues_repaired: int = 0
    storage_recoverable_bytes: int = 0
    storage_recoverable_formatted: str = "0 B"
    summary: Optional[Dict[str, Any]] = None
    issues: List[HealthIssueModel] = []


class HealthRepairRequest(BaseModel):
    issue_ids: Optional[List[str]] = Field(default=None, description="Specific issue IDs to repair, or all if empty")
    repair_type: Optional[str] = Field(default=None, description="clean_incomplete, reindex_orphans, remove_stale, all")


class StorageForecastResponse(BaseModel):
    total_bytes: int
    used_bytes: int
    free_bytes: int
    percent_used: float
    daily_download_rate_bytes: int
    daily_download_rate_formatted: str
    days_until_low_space: Optional[int] = None
    potential_recoverable_bytes: int = 0
    potential_recoverable_formatted: str = "0 B"
    status_summary: str


# --- Media Discovery & TMDB Schemas ---

class DiscoveryStatusResponse(BaseModel):
    enabled: bool
    tmdb_enabled: bool
    tmdb_configured: bool
    message: Optional[str] = None


class DiscoveredMovieItem(BaseModel):
    tmdb_id: int
    title: str
    original_title: Optional[str] = None
    release_date: Optional[str] = None
    year: Optional[int] = None
    overview: Optional[str] = None
    poster_path: Optional[str] = None
    poster_url: Optional[str] = None
    backdrop_path: Optional[str] = None
    backdrop_url: Optional[str] = None
    genres: List[str] = Field(default_factory=list)
    runtime: Optional[int] = None
    vote_average: float = 0.0
    vote_count: int = 0
    popularity: float = 0.0
    media_type: str = "movie"


class DiscoveredSeriesItem(BaseModel):
    tmdb_id: int
    name: str
    original_name: Optional[str] = None
    first_air_date: Optional[str] = None
    year: Optional[int] = None
    overview: Optional[str] = None
    poster_path: Optional[str] = None
    poster_url: Optional[str] = None
    backdrop_path: Optional[str] = None
    backdrop_url: Optional[str] = None
    genres: List[str] = Field(default_factory=list)
    number_of_seasons: int = 0
    number_of_episodes: int = 0
    vote_average: float = 0.0
    vote_count: int = 0
    popularity: float = 0.0
    media_type: str = "tv"


class MovieSearchResponse(BaseModel):
    query: str
    page: int
    total_pages: int
    total_results: int
    results: List[DiscoveredMovieItem]


class SeriesSearchResponse(BaseModel):
    query: str
    page: int
    total_pages: int
    total_results: int
    results: List[DiscoveredSeriesItem]


class MovieDetailResponse(BaseModel):
    tmdb_id: int
    title: str
    original_title: Optional[str] = None
    release_date: Optional[str] = None
    year: Optional[int] = None
    overview: Optional[str] = None
    poster_path: Optional[str] = None
    poster_url: Optional[str] = None
    backdrop_path: Optional[str] = None
    backdrop_url: Optional[str] = None
    genres: List[str] = Field(default_factory=list)
    runtime: Optional[int] = None
    vote_average: float = 0.0
    vote_count: int = 0
    popularity: float = 0.0
    status: Optional[str] = None
    tagline: Optional[str] = None
    imdb_id: Optional[str] = None
    media_type: str = "movie"


class SeasonSummaryItem(BaseModel):
    season_number: int
    name: str
    overview: Optional[str] = None
    air_date: Optional[str] = None
    episode_count: int = 0
    poster_path: Optional[str] = None
    poster_url: Optional[str] = None


class SeriesDetailResponse(BaseModel):
    tmdb_id: int
    name: str
    original_name: Optional[str] = None
    first_air_date: Optional[str] = None
    year: Optional[int] = None
    overview: Optional[str] = None
    poster_path: Optional[str] = None
    poster_url: Optional[str] = None
    backdrop_path: Optional[str] = None
    backdrop_url: Optional[str] = None
    genres: List[str] = Field(default_factory=list)
    number_of_seasons: int = 0
    number_of_episodes: int = 0
    vote_average: float = 0.0
    vote_count: int = 0
    popularity: float = 0.0
    status: Optional[str] = None
    tagline: Optional[str] = None
    seasons: List[SeasonSummaryItem] = Field(default_factory=list)
    media_type: str = "tv"


class EpisodeItem(BaseModel):
    episode_number: int
    season_number: int
    name: str
    overview: Optional[str] = None
    air_date: Optional[str] = None
    still_path: Optional[str] = None
    still_url: Optional[str] = None
    vote_average: float = 0.0
    runtime: Optional[int] = None


class SeasonDetailResponse(BaseModel):
    series_tmdb_id: int
    season_number: int
    name: str
    overview: Optional[str] = None
    air_date: Optional[str] = None
    poster_path: Optional[str] = None
    poster_url: Optional[str] = None
    episodes: List[EpisodeItem] = Field(default_factory=list)


class TMDBTestRequest(BaseModel):
    api_key: Optional[str] = None


class TMDBTestResponse(BaseModel):
    success: bool
    provider: str = "tmdb"
    latency_ms: Optional[int] = None
    status_code: Optional[int] = None
    error_code: Optional[str] = None
    message: str
    retryable: bool = False
    dns_ok: bool = True


# --- Prowlarr & Release Search Schemas (Phase 2) ---

class ProwlarrTestRequest(BaseModel):
    url: Optional[str] = None
    api_key: Optional[str] = None


class ProwlarrTestResponse(BaseModel):
    connected: bool
    version: Optional[str] = None
    indexer_count: int = 0
    message: str


class ProwlarrIndexerItem(BaseModel):
    id: int
    name: str
    enable: bool = True
    protocol: str = "torrent"
    privacy: Optional[str] = None
    status: str = "healthy"  # healthy, degraded, disabled, offline


class ProwlarrStatusResponse(BaseModel):
    configured: bool
    enabled: bool
    connected: bool
    version: Optional[str] = None
    indexer_count: int = 0
    healthy_indexers: int = 0
    unhealthy_indexers: int = 0
    message: Optional[str] = None


class ReleaseResult(BaseModel):
    id: str
    title: str
    indexer: str
    indexer_id: Optional[int] = None
    size_bytes: Optional[int] = None
    size_display: Optional[str] = None
    seeders: Optional[int] = None
    leechers: Optional[int] = None
    publish_date: Optional[str] = None
    age_days: Optional[int] = None
    download_url: Optional[str] = None
    magnet_url: Optional[str] = None
    info_hash: Optional[str] = None
    protocol: str = "torrent"
    categories: List[str] = Field(default_factory=list)
    resolution: Optional[str] = None
    codec: Optional[str] = None
    source: Optional[str] = None
    audio: Optional[str] = None
    release_group: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    match_score: int = 100
    freeleech: bool = False
    # Quality profile scoring fields (Phase 3)
    score: Optional[int] = None
    compatible: Optional[bool] = None
    score_reasons: List[str] = Field(default_factory=list)
    score_warnings: List[str] = Field(default_factory=list)


class ReleaseSearchRequest(BaseModel):
    query: Optional[str] = None
    search_type: str = "movie"  # movie, series, season, episode
    tmdb_id: Optional[int] = None
    title: Optional[str] = None
    year: Optional[int] = None
    season_number: Optional[int] = None
    episode_number: Optional[int] = None
    indexer_id: Optional[int] = None
    indexer_ids: Optional[List[int]] = None
    # Media Manager association & profile scoring (Phases 3 & 4)
    movie_id: Optional[str] = None
    series_id: Optional[str] = None
    episode_id: Optional[str] = None
    quality_profile_id: Optional[str] = None


class ReleaseSearchResponse(BaseModel):
    query: str
    search_type: str
    total_results: int
    indexers_searched: int = 0
    results: List[ReleaseResult] = Field(default_factory=list)


class ReleaseHandoffRequest(BaseModel):
    release_id: str
    title: str
    magnet_url: Optional[str] = None
    download_url: Optional[str] = None
    info_hash: Optional[str] = None
    interactive: bool = True
    movie_id: Optional[str] = None
    episode_id: Optional[str] = None
    job_type: Optional[str] = "NORMAL"
    is_upgrade: Optional[bool] = False
    previous_quality: Optional[str] = None
    upgrade_reason: Optional[str] = None


# --- Movie Manager & Quality Profiles & Root Folders Schemas (Phase 3) ---

class RootFolderResponse(BaseModel):
    id: str
    name: str
    path: str
    free_space_bytes: Optional[int] = None
    total_space_bytes: Optional[int] = None
    movie_count: int = 0
    created_at: float
    updated_at: float


class RootFolderCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    path: str = Field(..., min_length=1)


class RootFolderUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    path: Optional[str] = Field(default=None, min_length=1)


class QualityProfileResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    allowed_resolutions: List[str] = Field(default_factory=list)
    min_resolution: Optional[str] = None
    max_resolution: Optional[str] = None
    preferred_resolution: Optional[str] = None
    preferred_source: Optional[str] = None
    preferred_codec: Optional[str] = None
    min_size_bytes: int = 0
    max_size_bytes: int = 0
    preferred_audio: Optional[str] = None
    cutoff_quality: Optional[str] = None
    is_builtin: bool = False
    is_default: bool = False
    movie_count: int = 0
    created_at: float
    updated_at: float


class QualityProfileCreateRequest(BaseModel):
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    allowed_resolutions: List[str] = Field(default_factory=lambda: ["1080p"])
    min_resolution: Optional[str] = "720p"
    max_resolution: Optional[str] = "2160p"
    preferred_resolution: Optional[str] = "1080p"
    preferred_source: Optional[str] = "WEB-DL"
    preferred_codec: Optional[str] = "H.264"
    min_size_bytes: int = 0
    max_size_bytes: int = 0
    preferred_audio: Optional[str] = None
    cutoff_quality: Optional[str] = "1080p"
    is_default: bool = False


class QualityProfileUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    allowed_resolutions: Optional[List[str]] = None
    min_resolution: Optional[str] = None
    max_resolution: Optional[str] = None
    preferred_resolution: Optional[str] = None
    preferred_source: Optional[str] = None
    preferred_codec: Optional[str] = None
    min_size_bytes: Optional[int] = None
    max_size_bytes: Optional[int] = None
    preferred_audio: Optional[str] = None
    cutoff_quality: Optional[str] = None
    is_default: Optional[bool] = None


class ReleaseScoreResult(BaseModel):
    score: int
    compatible: bool
    score_reasons: List[str] = Field(default_factory=list)
    score_warnings: List[str] = Field(default_factory=list)


class MovieStatus(str, Enum):
    WANTED = "WANTED"
    MISSING = "MISSING"
    DOWNLOADING = "DOWNLOADING"
    DOWNLOADED = "DOWNLOADED"


class MovieResponse(BaseModel):
    id: str
    tmdb_id: int
    title: str
    original_title: Optional[str] = None
    year: Optional[int] = None
    overview: Optional[str] = None
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    runtime: Optional[int] = None
    genres: List[str] = Field(default_factory=list)
    release_date: Optional[str] = None
    root_folder_id: Optional[str] = None
    root_folder_name: Optional[str] = None
    root_folder_path: Optional[str] = None
    quality_profile_id: Optional[str] = None
    quality_profile_name: Optional[str] = None
    status: str = "WANTED"
    current_media_path: Optional[str] = None
    current_file_size: Optional[int] = None
    current_resolution: Optional[str] = None
    current_codec: Optional[str] = None
    current_source: Optional[str] = None
    monitored: bool = False
    automation_enabled: bool = False
    active_job_id: Optional[str] = None
    active_job_status: Optional[str] = None
    active_job_progress: Optional[float] = None
    created_at: float
    updated_at: float


class MovieCreateRequest(BaseModel):
    tmdb_id: int = Field(..., gt=0)
    root_folder_id: Optional[str] = None
    quality_profile_id: Optional[str] = None
    monitored: bool = False
    automation_enabled: bool = False


class MovieUpdateRequest(BaseModel):
    root_folder_id: Optional[str] = None
    quality_profile_id: Optional[str] = None
    status: Optional[str] = None
    monitored: Optional[bool] = None
    automation_enabled: Optional[bool] = None


class MovieListResponse(BaseModel):
    items: List[MovieResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50


# --- Series Manager & Seasons & Episodes Schemas (Phase 4) ---

class EpisodeStatus(str, Enum):
    WANTED = "WANTED"
    MISSING = "MISSING"
    DOWNLOADING = "DOWNLOADING"
    DOWNLOADED = "DOWNLOADED"
    UNAIRED = "UNAIRED"


class SeriesStatus(str, Enum):
    MISSING = "MISSING"
    PARTIAL = "PARTIAL"
    DOWNLOADING = "DOWNLOADING"
    DOWNLOADED = "DOWNLOADED"
    UNAIRED = "UNAIRED"


class EpisodeResponse(BaseModel):
    id: str
    series_id: str
    season_id: str
    tmdb_id: Optional[int] = None
    season_number: int
    episode_number: int
    name: str
    overview: Optional[str] = None
    still_path: Optional[str] = None
    still_url: Optional[str] = None
    air_date: Optional[str] = None
    runtime: Optional[int] = None
    status: str = "WANTED"
    current_media_path: Optional[str] = None
    current_file_size: Optional[int] = None
    current_resolution: Optional[str] = None
    current_codec: Optional[str] = None
    current_source: Optional[str] = None
    active_job_id: Optional[str] = None
    active_job_status: Optional[str] = None
    active_job_progress: Optional[float] = None
    created_at: float
    updated_at: float


class EpisodeUpdateRequest(BaseModel):
    status: Optional[str] = None


class SeasonResponse(BaseModel):
    id: str
    series_id: str
    tmdb_id: Optional[int] = None
    season_number: int
    name: str
    overview: Optional[str] = None
    poster_path: Optional[str] = None
    poster_url: Optional[str] = None
    air_date: Optional[str] = None
    episode_count: int = 0
    released_count: int = 0
    downloaded_count: int = 0
    downloading_count: int = 0
    missing_count: int = 0
    status: str = "MISSING"
    episodes: Optional[List[EpisodeResponse]] = None
    created_at: float
    updated_at: float


class SeriesResponse(BaseModel):
    id: str
    tmdb_id: int
    name: str
    original_name: Optional[str] = None
    year: Optional[int] = None
    overview: Optional[str] = None
    poster_path: Optional[str] = None
    poster_url: Optional[str] = None
    backdrop_path: Optional[str] = None
    backdrop_url: Optional[str] = None
    first_air_date: Optional[str] = None
    genres: List[str] = Field(default_factory=list)
    status: Optional[str] = None
    root_folder_id: Optional[str] = None
    root_folder_name: Optional[str] = None
    root_folder_path: Optional[str] = None
    quality_profile_id: Optional[str] = None
    quality_profile_name: Optional[str] = None
    seasons_count: int = 0
    total_episodes: int = 0
    released_episodes: int = 0
    downloaded_episodes: int = 0
    downloading_episodes: int = 0
    missing_episodes: int = 0
    series_status: str = "MISSING"
    monitored: bool = True
    automation_enabled: bool = False
    active_job_id: Optional[str] = None
    active_job_status: Optional[str] = None
    active_job_progress: Optional[float] = None
    seasons: Optional[List[SeasonResponse]] = None
    created_at: float
    updated_at: float


class SeriesCreateRequest(BaseModel):
    tmdb_id: int = Field(..., gt=0)
    root_folder_id: Optional[str] = None
    quality_profile_id: Optional[str] = None
    monitored: Optional[bool] = True
    automation_enabled: Optional[bool] = False


class SeriesUpdateRequest(BaseModel):
    root_folder_id: Optional[str] = None
    quality_profile_id: Optional[str] = None
    monitored: Optional[bool] = None
    automation_enabled: Optional[bool] = None


class SeriesListResponse(BaseModel):
    items: List[SeriesResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50


# =============================================================================
# PHASE 5 — MISSING MEDIA & MEDIA SEARCH ORCHESTRATOR SCHEMAS
# =============================================================================

class MissingMediaItem(BaseModel):
    media_type: str  # "movie" | "episode"
    id: str
    tmdb_id: Optional[int] = None
    title: str
    status: str  # "WANTED" | "MISSING"
    year: Optional[int] = None
    air_date: Optional[str] = None
    poster_path: Optional[str] = None
    poster_url: Optional[str] = None
    overview: Optional[str] = None
    series_id: Optional[str] = None
    series_title: Optional[str] = None
    season_id: Optional[str] = None
    season_number: Optional[int] = None
    episode_number: Optional[int] = None
    episode_title: Optional[str] = None
    quality_profile_id: Optional[str] = None
    quality_profile_name: Optional[str] = None
    root_folder_id: Optional[str] = None
    root_folder_name: Optional[str] = None
    root_folder_path: Optional[str] = None
    monitored: bool = True
    automation_enabled: bool = False
    active_job_id: Optional[str] = None
    active_job_status: Optional[str] = None
    active_job_progress: Optional[float] = None
    created_at: float
    updated_at: float


class MissingMediaCounts(BaseModel):
    movies: int = 0
    episodes: int = 0
    total: int = 0
    wanted: int = 0
    missing: int = 0
    monitored: int = 0
    unmonitored: int = 0
    automated: int = 0
    manual_only: int = 0


class MissingMediaResponse(BaseModel):
    items: List[MissingMediaItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50
    counts: MissingMediaCounts = Field(default_factory=MissingMediaCounts)


class MediaSearchRequest(BaseModel):
    target_type: str = Field(..., description="'movie', 'episode', or 'season'")
    movie_id: Optional[str] = None
    episode_id: Optional[str] = None
    series_id: Optional[str] = None
    season_id: Optional[str] = None
    season_number: Optional[int] = None
    episode_number: Optional[int] = None
    indexer_ids: Optional[List[int]] = None


class MediaSearchBatchTarget(BaseModel):
    type: str = Field(..., description="'movie' or 'episode'")
    id: str = Field(..., description="movie_id or episode_id")
    series_id: Optional[str] = None


class MediaSearchBatchRequest(BaseModel):
    targets: List[MediaSearchBatchTarget] = Field(..., min_length=1)
    indexer_ids: Optional[List[int]] = None


class MediaSearchBatchItemResult(BaseModel):
    target_type: str
    id: str
    title: str
    status: str  # 'SUCCESS', 'NO_RESULTS', 'TIMEOUT', 'AUTH_FAILED', 'UNAVAILABLE', 'ERROR'
    error_message: Optional[str] = None
    total_results: int = 0
    best_score: Optional[int] = None
    releases: List[ReleaseResult] = Field(default_factory=list)


class MediaSearchBatchResponse(BaseModel):
    total_targets: int
    successful_searches: int
    failed_searches: int
    results: List[MediaSearchBatchItemResult]


# =============================================================================
# PHASE 6 — AUTOMATIC MONITORING & SCHEDULED SEARCH SCHEMAS
# =============================================================================

class MonitoringSettings(BaseModel):
    monitoring_enabled: bool = False
    monitoring_interval_hours: int = 6
    allowed_monitoring_intervals: List[int] = Field(default_factory=lambda: [1, 2, 4, 6, 12, 24])
    monitoring_max_concurrency: int = 3
    monitoring_max_targets_per_cycle: int = 30
    monitoring_cooldown_hours: int = 6
    monitoring_history_retention_days: int = 30
    monitoring_search_movies: bool = True
    monitoring_search_episodes: bool = True


class MonitoringSettingsUpdateRequest(BaseModel):
    monitoring_enabled: Optional[bool] = None
    monitoring_interval_hours: Optional[int] = None
    monitoring_max_concurrency: Optional[int] = None
    monitoring_max_targets_per_cycle: Optional[int] = None
    monitoring_cooldown_hours: Optional[int] = None
    monitoring_history_retention_days: Optional[int] = None
    monitoring_search_movies: Optional[bool] = None
    monitoring_search_episodes: Optional[bool] = None


class MonitoringTodayStats(BaseModel):
    total_searches: int = 0
    successful_searches: int = 0
    failed_searches: int = 0
    results_found: int = 0


class MonitoringStatusResponse(BaseModel):
    enabled: bool
    is_running: bool
    last_run_at: Optional[float] = None
    next_run_at: Optional[float] = None
    interval_hours: int
    today_stats: MonitoringTodayStats = Field(default_factory=MonitoringTodayStats)
    monitored_movies_count: int = 0
    monitored_series_count: int = 0
    monitored_missing_targets_count: int = 0


class MonitoringHistoryItem(BaseModel):
    id: str
    target_type: str  # 'movie' | 'episode'
    target_id: str
    title: str
    trigger: str  # 'MANUAL' | 'SCHEDULED'
    status: str  # 'SUCCESS', 'NO_RESULTS', 'TIMEOUT', 'AUTH_FAILED', 'UNAVAILABLE', 'ERROR'
    result_count: int = 0
    best_score: Optional[int] = None
    duration_ms: Optional[int] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    started_at: float
    completed_at: float
    created_at: float


class MonitoringHistoryResponse(BaseModel):
    items: List[MonitoringHistoryItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50


class MonitoringManualSearchRequest(BaseModel):
    target_type: Optional[str] = None  # 'movie' | 'episode' | None
    target_id: Optional[str] = None


class MonitoringToggleRequest(BaseModel):
    monitored: Optional[bool] = None


# =============================================================================
# PHASE 7A — AUTOMATIC RELEASE SELECTION & MISSING-MEDIA DOWNLOAD SCHEMAS
# =============================================================================

class AutomationSettings(BaseModel):
    automation_enabled: bool = False
    automation_dry_run: bool = False
    automation_min_score: int = 75
    automation_min_seeders: int = 5
    automation_max_release_size_gb: float = 20.0
    automation_min_free_space_gb: float = 20.0
    automation_max_downloads_per_cycle: int = 3
    automation_max_downloads_per_day: int = 10
    automation_max_concurrent_downloads: int = 2
    automation_cooldown_hours: int = 6
    automation_max_total_size_per_cycle_gb: float = 30.0
    automation_max_total_size_per_day_gb: float = 100.0
    automation_require_compatible_release: bool = True
    automation_history_retention_days: int = 30
    automation_excluded_words: List[str] = Field(default_factory=list)
    automation_excluded_regex: Optional[str] = None
    automation_paused: bool = False
    automation_quality_upgrades_enabled: bool = False


class AutomationSettingsUpdateRequest(BaseModel):
    automation_enabled: Optional[bool] = None
    automation_dry_run: Optional[bool] = None
    automation_min_score: Optional[int] = None
    automation_min_seeders: Optional[int] = None
    automation_max_release_size_gb: Optional[float] = None
    automation_min_free_space_gb: Optional[float] = None
    automation_max_downloads_per_cycle: Optional[int] = None
    automation_max_downloads_per_day: Optional[int] = None
    automation_max_concurrent_downloads: Optional[int] = None
    automation_cooldown_hours: Optional[int] = None
    automation_max_total_size_per_cycle_gb: Optional[float] = None
    automation_max_total_size_per_day_gb: Optional[float] = None
    automation_require_compatible_release: Optional[bool] = None
    automation_history_retention_days: Optional[int] = None
    automation_excluded_words: Optional[List[str]] = None
    automation_excluded_regex: Optional[str] = None
    automation_paused: Optional[bool] = None
    automation_quality_upgrades_enabled: Optional[bool] = None


class AutomationCandidateEvaluation(BaseModel):
    release_id: str
    title: str
    indexer: Optional[str] = None
    size_bytes: int = 0
    seeders: int = 0
    score: int = 0
    compatible: bool = True
    accepted: bool = False
    rejection_reason: Optional[str] = None
    score_reasons: List[str] = Field(default_factory=list)
    score_warnings: List[str] = Field(default_factory=list)


class AutomationDecision(BaseModel):
    target_type: str  # 'movie' | 'episode'
    target_id: str
    title: str
    action: str  # 'AUTO_DOWNLOAD', 'DRY_RUN', 'SKIP', 'REJECT', 'BLOCKED'
    status: str  # 'SELECTED', 'NO_SAFE_CANDIDATE', 'SKIPPED', 'REJECTED', 'BLOCKED', 'FAILED'
    selected_candidate: Optional[ReleaseResult] = None
    selected_score: Optional[int] = None
    score_reasons: List[str] = Field(default_factory=list)
    rejection_reason: Optional[str] = None
    evaluations: List[AutomationCandidateEvaluation] = Field(default_factory=list)
    job_id: Optional[str] = None
    would_download: bool = False
    is_upgrade: bool = False
    previous_quality: Optional[str] = None
    upgrade_reason: Optional[str] = None


class AutomationStatusResponse(BaseModel):
    enabled: bool
    paused: bool
    dry_run: bool
    today_downloads_count: int = 0
    today_downloads_limit: int = 10
    today_downloaded_size_gb: float = 0.0
    today_size_limit_gb: float = 100.0
    active_downloads_count: int = 0
    active_downloads_limit: int = 2
    free_storage_gb: float = 0.0
    min_free_space_gb: float = 20.0
    last_run_at: Optional[float] = None
    monitored_targets_count: int = 0
    automated_targets_count: int = 0


class AutomationPreviewRequest(BaseModel):
    target_type: str  # 'movie' | 'episode'
    target_id: str


class AutomationPreviewResponse(BaseModel):
    target_type: str
    target_id: str
    title: str
    would_download: bool
    selected_candidate: Optional[ReleaseResult] = None
    selected_score: Optional[int] = None
    score_reasons: List[str] = Field(default_factory=list)
    rejection_reason: Optional[str] = None
    evaluations: List[AutomationCandidateEvaluation] = Field(default_factory=list)
    policy_summary: Dict[str, Any] = Field(default_factory=dict)
    is_upgrade: bool = False
    previous_quality: Optional[str] = None
    upgrade_delta: Optional[str] = None
    current_quality: Optional[Dict[str, Any]] = None


class AutomationHistoryItem(BaseModel):
    id: str
    target_type: str  # 'movie' | 'episode'
    target_id: str
    title: str
    trigger: str  # 'SCHEDULED' | 'MANUAL' | 'PREVIEW'
    action: str  # 'AUTO_DOWNLOAD' | 'DRY_RUN' | 'SKIP' | 'REJECT' | 'BLOCKED'
    status: str  # 'SELECTED' | 'NO_SAFE_CANDIDATE' | 'SKIPPED' | 'REJECTED' | 'BLOCKED' | 'FAILED'
    selected_release_title: Optional[str] = None
    selected_release_indexer: Optional[str] = None
    selected_release_size: Optional[int] = None
    selected_release_seeders: Optional[int] = None
    selected_release_score: Optional[int] = None
    selected_info_hash: Optional[str] = None
    score_reasons: List[str] = Field(default_factory=list)
    rejection_reason: Optional[str] = None
    job_id: Optional[str] = None
    dry_run: bool = False
    evaluations: List[Dict[str, Any]] = Field(default_factory=list)
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    created_at: float


class AutomationHistoryResponse(BaseModel):
    items: List[AutomationHistoryItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50
    total_pages: int = 1


class AutomationToggleRequest(BaseModel):
    automation_enabled: Optional[bool] = None


class AutomationManualRunRequest(BaseModel):
    target_type: Optional[str] = None
    target_id: Optional[str] = None


# =============================================================================
# Phase 8A — Import Engine & Verification Schemas
# =============================================================================

class VerifiedMediaInfo(BaseModel):
    path: str
    relative_path: Optional[str] = None
    size_bytes: int
    duration_seconds: Optional[float] = None
    media_type: str = "video"  # "video" | "audio"
    container: Optional[str] = None
    video_codec: Optional[str] = None
    video_profile: Optional[str] = None
    video_width: Optional[int] = None
    video_height: Optional[int] = None
    video_fps: Optional[float] = None
    video_bitrate: Optional[int] = None
    resolution: Optional[str] = None
    audio_codec: Optional[str] = None
    audio_channels: Optional[int] = None
    audio_sample_rate: Optional[int] = None
    video_stream_count: int = 0
    audio_stream_count: int = 0
    subtitle_stream_count: int = 0
    languages: List[str] = Field(default_factory=list)
    hdr: Optional[str] = None
    probe_status: str = "VERIFIED"  # "VERIFIED" | "FAILED" | "CORRUPT" | "STILL_WRITING"
    probe_error: Optional[str] = None
    probed_at: Optional[float] = None


class ExistingLibraryMediaInfo(BaseModel):
    path: Optional[str] = None
    size_bytes: Optional[int] = None
    resolution: Optional[str] = None
    source: Optional[str] = None
    codec: Optional[str] = None
    quality_summary: Optional[str] = None


class ImportCandidateResponse(BaseModel):
    id: str
    job_id: Optional[str] = None
    source_path: str
    source_relative_path: str
    source_root: str
    file_size_bytes: int
    source_mtime: float
    media_type: str = "video"
    movie_id: Optional[str] = None
    series_id: Optional[str] = None
    season_id: Optional[str] = None
    episode_id: Optional[str] = None
    match_type: str = "UNKNOWN"  # "MOVIE" | "EPISODE" | "UNKNOWN"
    match_title: Optional[str] = None
    match_year: Optional[int] = None
    match_season_number: Optional[int] = None
    match_episode_number: Optional[int] = None
    match_confidence: int = 0  # 0 - 100
    verification_status: str = "DISCOVERED"  # "DISCOVERED" | "VERIFYING" | "VERIFIED" | "FAILED" | "STILL_WRITING"
    candidate_status: str = "UNMATCHED"  # "UNMATCHED" | "NEEDS_REVIEW" | "READY" | "DUPLICATE" | "REJECTED" | "IMPORTED"
    duplicate_status: str = "NONE"  # "NONE" | "EXACT_MATCH" | "TARGET_EXISTS"
    quality_classification: str = "UNKNOWN"  # "UNKNOWN" | "UPGRADE" | "SAME" | "DOWNGRADE"
    current_library_path: Optional[str] = None
    current_library_media: Optional[ExistingLibraryMediaInfo] = None
    media_info: Optional[VerifiedMediaInfo] = None
    match_reasons: List[str] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)
    source_metadata: Dict[str, Any] = Field(default_factory=dict)
    fingerprint: Optional[str] = None
    rejection_reason: Optional[str] = None
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    destination_path: Optional[str] = None
    organization_operation_id: Optional[str] = None
    created_at: float
    updated_at: float
    verified_at: Optional[float] = None
    reviewed_at: Optional[float] = None


class ImportCandidateListResponse(BaseModel):
    items: List[ImportCandidateResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50
    total_pages: int = 1


class ImportCandidateReviewRequest(BaseModel):
    decision: str  # "READY" | "NEEDS_REVIEW" | "REJECTED"
    reason: Optional[str] = None


class ImportCandidateRejectRequest(BaseModel):
    reason: str


class ImportHistoryItem(BaseModel):
    id: str
    candidate_id: Optional[str] = None
    job_id: Optional[str] = None
    action: str
    status: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    title: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    created_at: float


class ImportHistoryResponse(BaseModel):
    items: List[ImportHistoryItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50
    total_pages: int = 1


# =============================================================================
# Phase 8B — Naming & Organization Schemas
# =============================================================================

class OrganizationPreview(BaseModel):
    candidate_id: str
    source_path: str
    source_size_bytes: int
    destination_root: str
    destination_directory: str
    destination_filename: str
    destination_path: str
    operation: str = "MOVE"
    target_type: str = "UNKNOWN"  # "MOVIE" | "EPISODE" | "UNKNOWN"
    target_id: Optional[str] = None
    target_title: Optional[str] = None
    conflict_status: str = "DESTINATION_AVAILABLE"
    # "DESTINATION_AVAILABLE" | "DESTINATION_EXISTS" | "IDENTICAL_DESTINATION" | "CONFLICT_DIFFERENT_MEDIA"
    # | "POSSIBLE_UPGRADE" | "POSSIBLE_DUPLICATE" | "UPGRADE_CONFLICT" | "DUPLICATE" | "INVALID_DESTINATION"
    conflict_details: Optional[str] = None
    quality_classification: str = "UNKNOWN"
    validation_status: str = "READY"  # "READY" | "BLOCKED" | "WARNING"
    can_organize: bool = False
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    estimated_action: str = "MOVE"
    safety_checklist: Dict[str, bool] = Field(default_factory=dict)


class OrganizationOperationResponse(BaseModel):
    id: str
    candidate_id: str
    source_path: str
    destination_path: str
    operation_type: str = "MOVE"
    status: str = "PREVIEWED"  # "PREVIEWED" | "APPROVED" | "EXECUTING" | "COMPLETED" | "FAILED" | "ABORTED" | "CONFLICT"
    source_size_before: Optional[int] = None
    source_fingerprint_before: Optional[str] = None
    destination_size_after: Optional[int] = None
    destination_fingerprint_after: Optional[str] = None
    conflict_status: str = "DESTINATION_AVAILABLE"
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


class OrganizationOperationListResponse(BaseModel):
    items: List[OrganizationOperationResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50
    total_pages: int = 1


# =============================================================================
# Phase 8C — Quality Upgrade Replacement Schemas
# =============================================================================

class QualityUpgradePreview(BaseModel):
    candidate_id: str
    movie_id: Optional[str] = None
    series_id: Optional[str] = None
    episode_id: Optional[str] = None
    target_type: str = "UNKNOWN"
    target_title: Optional[str] = None
    existing_media_path: str
    existing_media_size: int
    existing_media_quality: Dict[str, Any] = Field(default_factory=dict)
    candidate_source_path: str
    candidate_source_size: int
    candidate_quality: Dict[str, Any] = Field(default_factory=dict)
    destination_path: str
    quality_classification: str = "UNKNOWN"
    quality_delta: Optional[str] = None
    quality_score_before: Optional[float] = None
    quality_score_after: Optional[float] = None
    is_upgrade: bool = False
    can_replace: bool = False
    safety_checklist: Dict[str, bool] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    recommended_policy: str = "ARCHIVE"
    supported_policies: List[str] = Field(default_factory=lambda: ["ARCHIVE", "DELETE", "KEEP"])


class QualityUpgradeReplaceRequest(BaseModel):
    replacement_policy: str = "ARCHIVE"  # "ARCHIVE" | "DELETE" | "KEEP"
    confirm_delete: bool = False


class QualityUpgradeReplacementResponse(BaseModel):
    id: str
    candidate_id: str
    movie_id: Optional[str] = None
    series_id: Optional[str] = None
    episode_id: Optional[str] = None
    existing_library_path: str
    candidate_source_path: str
    destination_path: str
    staging_path: Optional[str] = None
    old_media_backup_path: Optional[str] = None
    archive_path: Optional[str] = None
    old_media_fingerprint: str
    old_media_size: int
    old_media_mtime: float
    old_media_quality: Dict[str, Any] = Field(default_factory=dict)
    new_media_fingerprint: Optional[str] = None
    new_media_size: Optional[int] = None
    new_media_mtime: Optional[float] = None
    new_media_quality: Dict[str, Any] = Field(default_factory=dict)
    quality_score_before: Optional[float] = None
    quality_score_after: Optional[float] = None
    upgrade_reason: Optional[str] = None
    replacement_policy: str = "ARCHIVE"
    status: str = "PREVIEWED"
    rollback_status: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: float
    approved_at: Optional[float] = None
    started_at: Optional[float] = None
    staging_completed_at: Optional[float] = None
    replacement_committed_at: Optional[float] = None
    completed_at: Optional[float] = None
    archived_at: Optional[float] = None
    deleted_at: Optional[float] = None


class QualityUpgradeReplacementListResponse(BaseModel):
    items: List[QualityUpgradeReplacementResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50
    total_pages: int = 1








