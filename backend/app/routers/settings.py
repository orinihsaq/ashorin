from fastapi import APIRouter, HTTPException
from app.models.schemas import SettingsResponse, SettingsUpdateRequest
from app.services.settings_service import ALLOWED_RETENTION_DAYS, settings_service
from app.utils.errors import ValidationError
from app.utils.logger import logger

router = APIRouter(prefix="/api/settings", tags=["Settings"])


@router.get("", response_model=SettingsResponse)
async def get_settings_endpoint() -> SettingsResponse:
    """Returns the current server-side configuration, including download retention policy."""
    data = settings_service.get_settings()
    return SettingsResponse(**data)


@router.patch("", response_model=SettingsResponse)
async def update_settings_endpoint(req: SettingsUpdateRequest) -> SettingsResponse:
    """
    Updates server-side download retention settings.
    Validates that retention_days is strictly one of 7, 14, 21, or 30 days.
    Settings are persisted to survive container restarts.
    """
    if req.retention_days is not None and req.retention_days not in ALLOWED_RETENTION_DAYS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid retention_days '{req.retention_days}'. Allowed values are strictly: {ALLOWED_RETENTION_DAYS}."
        )

    try:
        updated = settings_service.update_settings(
            retention_enabled=req.retention_enabled,
            retention_days=req.retention_days,
            media_discovery_enabled=req.media_discovery_enabled,
            tmdb_enabled=req.tmdb_enabled,
            tmdb_api_key=req.tmdb_api_key,
            prowlarr_enabled=req.prowlarr_enabled,
            prowlarr_url=req.prowlarr_url,
            prowlarr_api_key=req.prowlarr_api_key,
            prowlarr_timeout_seconds=req.prowlarr_timeout_seconds,
        )
        return SettingsResponse(**updated)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to save settings.")
