import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Set
from app.models.schemas import JobResponse, JobStatus
from app.services.file_service import FileService


@dataclass
class Job:
    id: str
    url: str
    title: Optional[str] = None
    thumbnail: Optional[str] = None
    status: JobStatus = JobStatus.QUEUED
    progress: float = 0.0
    speed: Optional[str] = None
    eta: Optional[str] = None
    current_stage: str = "Queued"
    downloaded_bytes: int = 0
    total_bytes: Optional[int] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    output_filename: Optional[str] = None
    output_filesize: Optional[int] = None
    output_path: Optional[Path] = None
    temp_dir: Optional[Path] = None
    error_message: Optional[str] = None

    # Process & Download Configuration
    config: Optional[Any] = None
    resolution: Optional[str] = "best"
    audio_only: bool = False
    audio_format: Optional[str] = "mp3"
    output_container: Optional[str] = "mp4"

    # Subprocess & cancellation
    process: Optional[asyncio.subprocess.Process] = None
    is_cancelled: bool = False

    # SSE listeners (queues waiting for updates)
    listeners: Set[asyncio.Queue] = field(default_factory=set)

    def to_response(self) -> JobResponse:
        download_url = f"/api/files/{self.id}" if self.status == JobStatus.COMPLETED and self.output_filename else None
        filesize_fmt = FileService.format_bytes(self.output_filesize) if self.output_filesize else None

        # Build clean config summary
        if self.config:
            is_audio = getattr(self.config, 'audio_mode', '') == 'audio_only'
            mode_str = "Audio Only" if is_audio else getattr(self.config, 'quality', 'best')
            cont_str = getattr(self.config, 'output_container', 'mp4').upper()
            preset_str = getattr(self.config, 'preset', 'recommended').title()
            cfg_summary = f"{mode_str} · {cont_str} · {preset_str}"
        else:
            cfg_summary = f"{self.resolution or 'Best'} · {(self.output_container or 'mp4').upper()}"

        return JobResponse(
            id=self.id,
            url=self.url,
            title=self.title,
            thumbnail=self.thumbnail,
            status=self.status,
            progress=round(self.progress, 1),
            speed=self.speed,
            eta=self.eta,
            current_stage=self.current_stage,
            downloaded_bytes=self.downloaded_bytes,
            total_bytes=self.total_bytes,
            created_at=self.created_at,
            started_at=self.started_at,
            completed_at=self.completed_at,
            output_filename=self.output_filename,
            output_filesize=self.output_filesize,
            output_filesize_formatted=filesize_fmt,
            error_message=self.error_message,
            download_url=download_url,
            config_summary=cfg_summary,
        )

    def emit_event(self) -> None:
        """Broadcast updated state to all connected SSE clients."""
        payload = self.to_response().model_dump()
        for q in list(self.listeners):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                pass
            except Exception:
                pass
