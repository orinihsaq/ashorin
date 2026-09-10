from fastapi import APIRouter
from app.models.schemas import PresetsResponse
from app.services.presets import PresetService

router = APIRouter(prefix="/api/presets", tags=["Presets"])


@router.get("", response_model=PresetsResponse)
async def get_presets_endpoint() -> PresetsResponse:
    """
    Returns canonical download configuration presets:
    - Recommended (Safe standard)
    - Best Quality (Maximum resolution + MKV + chapters)
    - Audio Only (Pristine 320k MP3 + artwork)
    - Small File (Efficient 720p H.264)
    - Archive (Preservation with subtitles & chapters)
    """
    return PresetService.get_all_presets()
