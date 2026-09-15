from fastapi import APIRouter, HTTPException
from app.models.schemas import PreflightRequest, PreflightResponse
from app.services.preflight_service import PreflightService
from app.utils.logger import logger

router = APIRouter(prefix="/api/preflight", tags=["Download Preflight"])


@router.post("", response_model=PreflightResponse)
async def run_preflight(req: PreflightRequest):
    """
    Analyzes target media or collection before downloading.
    Evaluates duplicate items, quality upgrades, storage availability,
    resolved profile/recipe, and destination folder.
    """
    try:
        res = await PreflightService.analyze_preflight(
            url=req.url,
            profile_id=req.profile_id,
            recipe_id=req.recipe_id,
            selected_indices=req.selected_indices,
            dry_run=req.dry_run,
        )
        return res
    except Exception as e:
        logger.error(f"Preflight analysis failed: {e}")
        raise HTTPException(status_code=400, detail=f"Preflight analysis failed: {str(e)}")
