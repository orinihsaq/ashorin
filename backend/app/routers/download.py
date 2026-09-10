from fastapi import APIRouter, HTTPException
from app.models.schemas import DownloadRequest, DownloadResponse
from app.services.job_manager import job_manager
from app.services.security import SecurityService
from app.utils.errors import AppException
from app.utils.logger import logger

router = APIRouter(prefix="/api", tags=["Downloads"])


@router.post("/download", response_model=DownloadResponse)
async def create_download_endpoint(req: DownloadRequest) -> DownloadResponse:
    """
    Submits a media download job with format, audio-only, and container preferences.
    Performs URL validation and SSRF filtering before queuing.
    """
    try:
        valid_url = SecurityService.validate_url(req.url)
        # Re-assign validated URL
        req.url = valid_url

        job = await job_manager.create_job(req)
        return DownloadResponse(
            job_id=job.id,
            status=job.status,
            message="Download job queued successfully.",
        )
    except AppException as e:
        logger.warning(f"Download request rejected for {req.url}: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.exception(f"Unexpected error queuing download for {req.url}: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue download job.")
