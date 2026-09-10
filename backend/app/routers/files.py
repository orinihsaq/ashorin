from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.config import settings
from app.models.schemas import JobStatus
from app.services.file_service import FileService
from app.services.job_manager import job_manager
from app.utils.errors import JobNotFoundError
from app.utils.logger import logger

router = APIRouter(prefix="/api/files", tags=["Files"])


@router.api_route("/{job_id}", methods=["GET", "HEAD"])
async def download_file_endpoint(job_id: str):
    """
    Downloads the completed media file to the browser.
    Validates file existence and path containment.
    """
    try:
        job = job_manager.get_job(job_id)
    except JobNotFoundError:
        raise HTTPException(status_code=404, detail="Download job not found.")

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot download file. Job status is '{job.status.value}'.",
        )

    if not job.output_path or not job.output_path.exists():
        raise HTTPException(status_code=404, detail="Downloaded media file not found on disk.")

    # Validate that output_path is safely contained in download directory
    try:
        safe_path = FileService.get_safe_file_path(settings.download_path, job.output_path.name)
    except Exception:
        raise HTTPException(status_code=403, detail="Access to file path is forbidden.")

    if not safe_path.exists():
        raise HTTPException(status_code=404, detail="File not found in storage.")

    download_name = job.output_filename or safe_path.name
    # Ensure safe ascii / quoted disposition name
    content_disp = f'attachment; filename="{download_name}"'

    return FileResponse(
        path=str(safe_path),
        filename=download_name,
        media_type="application/octet-stream",
        headers={"Content-Disposition": content_disp},
    )
