from enum import Enum
from typing import List, Optional
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
    filesize_approx: Optional[str] = None
    ext: str = "mp4"


class AudioQualityOption(BaseModel):
    label: str               # e.g., "MP3 (Best Audio)"
    format: str              # e.g., "mp3", "m4a", "wav"
    ext: str = "mp3"


class AnalyzeRequest(BaseModel):
    url: str = Field(..., description="The media URL to analyze")


class AnalyzeResponse(BaseModel):
    url: str
    title: str
    thumbnail: Optional[str] = None
    duration: Optional[int] = None
    duration_string: Optional[str] = None
    uploader: Optional[str] = None
    webpage_url: str
    extractor: str
    video_available: bool = True
    audio_available: bool = True
    video_options: List[VideoQualityOption] = []
    audio_options: List[AudioQualityOption] = []
    supported_containers: List[str] = ["mp4", "mkv", "webm"]


class DownloadRequest(BaseModel):
    url: str = Field(..., description="Target media URL")
    title: Optional[str] = None
    resolution: Optional[str] = Field(default="best", description="Resolution: best, 1080p, 720p, 480p, 360p")
    audio_only: bool = Field(default=False, description="Extract audio only")
    audio_format: Optional[str] = Field(default="mp3", description="Audio format: mp3, m4a, wav")
    output_container: Optional[str] = Field(default="mp4", description="Output container: mp4, mkv, webm")


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
