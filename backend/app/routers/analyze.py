from fastapi import APIRouter, HTTPException
from app.models.schemas import AnalyzeRequest, AnalyzeResponse
from app.services.security import SecurityService
from app.services.yt_dlp import YtDlpService
from app.utils.errors import AppException
from app.utils.logger import logger

router = APIRouter(prefix="/api", tags=["Analysis"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_url_endpoint(req: AnalyzeRequest) -> AnalyzeResponse:
    """
    Analyzes an untrusted media URL using yt-dlp extraction only.
    Validates URL scheme and protects against SSRF.
    Returns normalized metadata and available quality formats.
    """
    try:
        valid_url = SecurityService.validate_url(req.url)
        data = await YtDlpService.analyze_url(valid_url)
        return data
    except AppException as e:
        logger.warning(f"Analysis error for {req.url}: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.exception(f"Unexpected error analyzing {req.url}: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred during URL analysis.")
