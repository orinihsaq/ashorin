from typing import Optional
from fastapi import APIRouter, Header, HTTPException, Query
from app.models.schemas import (
    DownloadConfig,
    DownloadRequest,
    DownloadResponse,
    JobResponse,
    MediaListResponse,
)
from app.repositories.api_key_repository import ApiKeyRepository
from app.repositories.profile_repository import ProfileRepository
from app.services.duplicate_detector import DuplicateDetector
from app.services.job_manager import job_manager
from app.services.security import SecurityService
from app.routers.library import list_library

router = APIRouter(prefix="/api/v1", tags=["Public Automation API (v1)"])


def authenticate_api_key(x_api_key: Optional[str] = Header(None)) -> dict:
    """Verifies incoming X-API-Key header against hashed API keys."""
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="API Key missing. Provide 'X-API-Key' header.",
        )

    key_record = ApiKeyRepository.verify_key(x_api_key)
    if not key_record:
        raise HTTPException(
            status_code=401,
            detail="Invalid or revoked API Key.",
        )
    return key_record


@router.post("/jobs", response_model=DownloadResponse)
async def submit_automation_job(
    req: DownloadRequest,
    x_api_key: Optional[str] = Header(None),
):
    """
    Submits a media download request via the Public Automation API.
    Requires valid 'X-API-Key' authentication header.
    """
    authenticate_api_key(x_api_key)

    # Detect input type first before validation
    from app.services.input_router import detect_input_type, InputType
    from app.services.torrent.magnet import MagnetParser, MagnetValidator
    from app.models.schemas import TorrentDownloadConfig

    itype = detect_input_type(req.url)
    if itype == InputType.MAGNET_URI:
        validated_url = MagnetValidator.validate_uri(req.url)
        req.provider = "torrent"
        req.input_type = "magnet"
    elif itype == InputType.TORRENT_FILE:
        validated_url = req.url.strip()
        req.provider = "torrent"
        req.input_type = "torrent_file"
    elif itype in (InputType.HTTP_URL, InputType.HTTPS_URL):
        validated_url = SecurityService.validate_http_url(req.url)
        if not req.provider:
            req.provider = "ytdlp"
        if not req.input_type:
            req.input_type = "url"
    else:
        raise HTTPException(
            status_code=422,
            detail="Unsupported input type. Only HTTP, HTTPS, magnet URIs, and .torrent files are supported.",
        )

    req.url = validated_url

    if req.provider == "torrent" and MagnetParser.is_magnet_url(validated_url):
        ih = MagnetParser.extract_info_hash(validated_url)
        if ih and not req.torrent_config:
            req.torrent_config = TorrentDownloadConfig(info_hash=ih, magnet_uri=validated_url)
        elif ih and req.torrent_config and not req.torrent_config.info_hash:
            req.torrent_config.info_hash = ih

    # Check duplicate unless overridden
    if not getattr(req, "override_duplicate", False):
        is_dup, dup_reason, existing = DuplicateDetector.check_duplicate(validated_url)
        if is_dup:
            raise HTTPException(
                status_code=409,
                detail=f"Duplicate detected: {dup_reason}",
            )

    # If profile_id specified, resolve config
    if req.profile_id and not req.config:
        prof = ProfileRepository.get_profile(req.profile_id)
        if prof:
            req.config = DownloadConfig(**prof.get("config", {}))

    job = await job_manager.create_job(req)
    return DownloadResponse(
        job_id=job.id,
        status=job.status,
        message="Job accepted and queued for execution.",
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_automation_job(
    job_id: str,
    x_api_key: Optional[str] = Header(None),
):
    """Retrieves current execution status of a submitted job."""
    authenticate_api_key(x_api_key)
    job = job_manager.get_job(job_id)
    return job.to_response()


@router.delete("/jobs/{job_id}")
async def cancel_automation_job(
    job_id: str,
    x_api_key: Optional[str] = Header(None),
):
    """Cancels an active or queued job."""
    authenticate_api_key(x_api_key)
    await job_manager.cancel_job(job_id)
    return {"status": "success", "message": f"Job {job_id} cancelled."}


@router.get("/library", response_model=MediaListResponse)
async def get_automation_library(
    type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    x_api_key: Optional[str] = Header(None),
):
    """Queries media library via API key."""
    authenticate_api_key(x_api_key)
    return await list_library(
        type=type,
        search=search,
        page=page,
        page_size=page_size,
    )


# --- V1 Watchers & Recipes Automation ---

from app.models.schemas import WatcherCreateRequest, WatcherModel, RecipeModel
from app.repositories.watcher_repository import WatcherRepository
from app.repositories.recipe_repository import RecipeRepository
from app.services.watcher_service import WatcherService


@router.get("/watchers", response_model=list[WatcherModel])
async def list_automation_watchers(x_api_key: Optional[str] = Header(None)):
    """Lists configured watchers via API key."""
    authenticate_api_key(x_api_key)
    watchers = WatcherRepository.list_watchers()
    return [WatcherModel(**w) for w in watchers]


@router.post("/watchers", response_model=WatcherModel)
async def create_automation_watcher(
    req: WatcherCreateRequest,
    x_api_key: Optional[str] = Header(None),
):
    """Creates a new collection watcher via API key."""
    authenticate_api_key(x_api_key)
    validated_url = SecurityService.validate_url(req.source_url)
    data = req.model_dump()
    data["source_url"] = validated_url
    created = WatcherRepository.create_watcher(data)
    return WatcherModel(**created)


@router.post("/watchers/{watcher_id}/sync")
async def sync_automation_watcher(
    watcher_id: str,
    x_api_key: Optional[str] = Header(None),
):
    """Triggers an immediate sync for a watcher via API key."""
    authenticate_api_key(x_api_key)
    existing = WatcherRepository.get_watcher(watcher_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Watcher not found")
    return await WatcherService.sync_watcher(watcher_id, is_manual=True)


@router.get("/recipes", response_model=list[RecipeModel])
async def list_automation_recipes(x_api_key: Optional[str] = Header(None)):
    """Lists all available recipes via API key."""
    authenticate_api_key(x_api_key)
    recipes = RecipeRepository.list_recipes()
    return [RecipeModel(**r) for r in recipes]


# --- V1 BitTorrent Automation ---

@router.post("/torrents", response_model=DownloadResponse)
async def submit_automation_torrent(
    req: DownloadRequest,
    x_api_key: Optional[str] = Header(None),
):
    """Submits a magnet URI or torrent download job via API key."""
    authenticate_api_key(x_api_key)
    req.provider = "torrent"
    job = await job_manager.create_job(req)
    return DownloadResponse(
        job_id=job.id,
        status=job.status,
        message="Torrent download job created successfully.",
    )


@router.get("/torrents", response_model=list[JobResponse])
async def list_automation_torrents(x_api_key: Optional[str] = Header(None)):
    """Lists all torrent jobs via API key."""
    authenticate_api_key(x_api_key)
    all_jobs = job_manager.list_jobs(include_history=True)
    return [j for j in all_jobs if j.provider == "torrent"]


@router.get("/torrents/{job_id}", response_model=JobResponse)
async def get_automation_torrent(job_id: str, x_api_key: Optional[str] = Header(None)):
    """Gets torrent job status and telemetry via API key."""
    authenticate_api_key(x_api_key)
    try:
        job = job_manager.get_job(job_id)
        return job.to_response()
    except Exception:
        raise HTTPException(status_code=404, detail="Torrent job not found")


@router.post("/torrents/{job_id}/pause", response_model=JobResponse)
async def pause_automation_torrent(job_id: str, x_api_key: Optional[str] = Header(None)):
    """Pauses torrent download via API key."""
    authenticate_api_key(x_api_key)
    job = await job_manager.pause_job(job_id)
    return job.to_response()


@router.post("/torrents/{job_id}/resume", response_model=JobResponse)
async def resume_automation_torrent(job_id: str, x_api_key: Optional[str] = Header(None)):
    """Resumes torrent download via API key."""
    authenticate_api_key(x_api_key)
    job = await job_manager.resume_job(job_id)
    return job.to_response()


@router.post("/torrents/{job_id}/recheck", response_model=JobResponse)
async def recheck_automation_torrent(job_id: str, x_api_key: Optional[str] = Header(None)):
    """Forces hash recheck for a torrent via API key."""
    authenticate_api_key(x_api_key)
    job = await job_manager.recheck_job(job_id)
    return job.to_response()


@router.post("/torrents/{job_id}/stop-seeding", response_model=JobResponse)
async def stop_seeding_automation_torrent(job_id: str, x_api_key: Optional[str] = Header(None)):
    """Stops seeding a torrent via API key."""
    authenticate_api_key(x_api_key)
    job = await job_manager.stop_seeding_job(job_id)
    return job.to_response()
