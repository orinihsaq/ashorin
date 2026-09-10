from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    ANALYZING = "ANALYZING"
    DOWNLOADING = "DOWNLOADING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


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
    playlist_mode: str = Field(default="single", description="single or playlist")
    playlist_items: Optional[str] = Field(default=None, description="Playlist items range (e.g. 1-10)")


class PresetDefinition(BaseModel):
    id: str
    name: str
    description: str
    badge: Optional[str] = None
    config: DownloadConfig


class PresetsResponse(BaseModel):
    presets: List[PresetDefinition]
    default_preset: str = "recommended"


class DownloadRequest(BaseModel):
    url: str = Field(..., description="Target media URL")
    title: Optional[str] = None
    config: Optional[DownloadConfig] = None
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


class DownloadResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str = "Download job queued successfully."


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
    download_url: Optional[str] = None
    config_summary: Optional[str] = None


class JobListResponse(BaseModel):
    jobs: List[JobResponse]
    total: int
    active_count: int


class CancelResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str


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
