import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, HTTPException, UploadFile
from app.config import settings
from app.models.schemas import JobResponse, TorrentMetadataResponse
from app.repositories.torrent_repository import TorrentRepository
from app.services.job_manager import job_manager
from app.services.torrent.torrent_service import torrent_service
from app.utils.errors import AppException, FileTooLargeError, ValidationError
from app.utils.logger import logger

from pydantic import BaseModel

router = APIRouter(prefix="/api/torrents", tags=["BitTorrent"])


class StartTorrentRequest(BaseModel):
    selected_files: Optional[List[int]] = None
    file_priorities: Optional[Dict[int, str]] = None
    destination_folder: Optional[str] = None
    seeding_mode: Optional[str] = None


@router.post("/{job_id}/start", response_model=JobResponse)
async def start_torrent_endpoint(job_id: str, req: Optional[StartTorrentRequest] = None) -> JobResponse:
    """Starts download for a torrent job in READY or WAITING_FOR_SELECTION state or paused."""
    try:
        job = await job_manager.start_ready_job(
            job_id,
            selected_files=req.selected_files if req else None,
            file_priorities=req.file_priorities if req else None,
            destination_folder=req.destination_folder if req else None,
            seeding_mode=req.seeding_mode if req else None,
        )
        return job.to_response()
    except Exception as e:
        logger.exception(f"Error starting torrent job [{job_id}]: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to start torrent: {e}")


@router.post("/upload", response_model=TorrentMetadataResponse)
async def upload_torrent_file_endpoint(
    file: UploadFile = File(...),
) -> TorrentMetadataResponse:
    """
    Accepts a .torrent file upload (capped at 10MB).
    Parses bencode dictionary, validates info dictionary, extracts SHA1 info_hash,
    and returns metadata & file manifest for user inspection.
    """
    if not file.filename or not file.filename.lower().endswith(".torrent"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Only .torrent files are accepted.",
        )

    try:
        content = await file.read()
        if len(content) > settings.max_torrent_file_size_bytes:
            raise FileTooLargeError(
                f"Uploaded .torrent file exceeds maximum allowed size of {settings.MAX_TORRENT_FILE_SIZE}."
            )

        saved_path, metadata = await torrent_service.handle_torrent_upload(
            filename=file.filename,
            file_bytes=content,
        )
        return metadata
    except AppException as e:
        logger.warning(f"Torrent upload validation error: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.exception(f"Unexpected error processing .torrent upload: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse .torrent file: {e}",
        )


@router.post("/{job_id}/pause", response_model=JobResponse)
async def pause_torrent_endpoint(job_id: str) -> JobResponse:
    """Pauses an active BitTorrent download/seeding session."""
    try:
        job = await job_manager.pause_job(job_id)
        return job.to_response()
    except Exception as e:
        logger.exception(f"Error pausing torrent job [{job_id}]: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to pause torrent: {e}")


@router.post("/{job_id}/resume", response_model=JobResponse)
async def resume_torrent_endpoint(job_id: str) -> JobResponse:
    """Resumes a paused BitTorrent download/seeding session."""
    try:
        job = await job_manager.resume_job(job_id)
        return job.to_response()
    except Exception as e:
        logger.exception(f"Error resuming torrent job [{job_id}]: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to resume torrent: {e}")


@router.post("/{job_id}/recheck", response_model=JobResponse)
async def recheck_torrent_endpoint(job_id: str) -> JobResponse:
    """Triggers hash verification of existing downloaded pieces on disk."""
    try:
        job = await job_manager.recheck_job(job_id)
        return job.to_response()
    except Exception as e:
        logger.exception(f"Error rechecking torrent job [{job_id}]: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to recheck torrent: {e}")


@router.post("/{job_id}/stop-seeding", response_model=JobResponse)
async def stop_seeding_endpoint(job_id: str) -> JobResponse:
    """Terminates seeding mode early and transitions job to COMPLETED."""
    try:
        job = await job_manager.stop_seeding_job(job_id)
        return job.to_response()
    except Exception as e:
        logger.exception(f"Error stopping seeding for torrent job [{job_id}]: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to stop seeding: {e}")


@router.get("", response_model=List[Dict[str, Any]])
async def list_torrents_endpoint() -> List[Dict[str, Any]]:
    """Returns database list of all tracked torrents."""
    return TorrentRepository.list_active()


@router.get("/{job_id}", response_model=JobResponse)
async def get_torrent_job_endpoint(job_id: str) -> JobResponse:
    """Returns Job status and current live BitTorrent telemetry."""
    try:
        job = job_manager.get_job(job_id)
        return job.to_response()
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Torrent job not found: {e}")


@router.api_route("/{job_id}/download", methods=["GET", "HEAD"])
async def download_torrent_files_endpoint(job_id: str):
    """Convenience alias downloading completed torrent single file or ZIP archive."""
    from app.routers.files import download_file_endpoint
    return await download_file_endpoint(job_id)


@router.post("/{job_id}/archive")
async def prepare_torrent_archive_endpoint(job_id: str) -> Dict[str, Any]:
    """
    Prepares or retrieves archive metadata for completed multi-file torrent (Section 21).
    Returns archive_name, archive_path, file_count, and archive_size.
    """
    try:
        job = job_manager.get_job(job_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Torrent job not found")

    if not job.output_path or not job.output_path.exists():
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "TORRENT_OUTPUT_NOT_FOUND",
                    "message": "The completed torrent files are no longer available.",
                }
            },
        )

    from app.services.archive_service import ArchiveService
    from app.services.file_service import FileService

    content_root = ArchiveService.resolve_content_root(job.output_path)
    archive_stem = FileService.sanitize_filename(job.output_filename or content_root.name or "torrent")
    archive_name = archive_stem if archive_stem.lower().endswith(".zip") else f"{archive_stem}.zip"

    try:
        zip_path = ArchiveService.create_torrent_zip(
            source_dir=content_root,
            archive_name=archive_name,
            job_id=job.id,
        )
    except Exception as e:
        logger.exception(f"Failed to generate torrent archive for {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to package archive: {e}")

    meta = ArchiveService.get_torrent_archive_metadata(
        job_id=job.id,
        archive_name=archive_name,
        source_dir=content_root,
    )
    return meta

