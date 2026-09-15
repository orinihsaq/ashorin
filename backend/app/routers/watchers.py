from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import (
    WatcherCreateRequest,
    WatcherModel,
    WatcherRunModel,
    WatcherUpdateRequest,
)
from app.repositories.watcher_repository import WatcherRepository
from app.services.security import SecurityService
from app.services.watcher_service import WatcherService
from app.utils.logger import logger

router = APIRouter(prefix="/api/watchers", tags=["Collection Watchers"])


@router.get("", response_model=List[WatcherModel])
async def list_watchers(status: Optional[str] = Query(None)):
    """Lists all configured collection watchers."""
    watchers = WatcherRepository.list_watchers(status=status)
    return [WatcherModel(**w) for w in watchers]


@router.post("", response_model=WatcherModel)
async def create_watcher(req: WatcherCreateRequest):
    """Creates a persistent watcher to monitor and keep a collection synced."""
    try:
        validated_url = SecurityService.validate_url(req.source_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid or restricted source URL: {str(e)}")

    data = req.model_dump()
    data["source_url"] = validated_url
    created = WatcherRepository.create_watcher(data)
    return WatcherModel(**created)


@router.get("/{watcher_id}", response_model=WatcherModel)
async def get_watcher(watcher_id: str):
    """Retrieves full watcher details and recent sync runs."""
    watcher = WatcherRepository.get_watcher(watcher_id)
    if not watcher:
        raise HTTPException(status_code=404, detail="Watcher not found")
    return WatcherModel(**watcher)


@router.patch("/{watcher_id}", response_model=WatcherModel)
async def update_watcher(watcher_id: str, req: WatcherUpdateRequest):
    """Updates watcher configuration, schedule, or rules."""
    existing = WatcherRepository.get_watcher(watcher_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Watcher not found")

    updated = WatcherRepository.update_watcher(watcher_id, req.model_dump(exclude_unset=True))
    return WatcherModel(**updated)


@router.delete("/{watcher_id}")
async def delete_watcher(watcher_id: str):
    """Permanently deletes a collection watcher."""
    success = WatcherRepository.delete_watcher(watcher_id)
    if not success:
        raise HTTPException(status_code=404, detail="Watcher not found")
    return {"status": "success", "message": "Watcher deleted"}


@router.post("/{watcher_id}/sync")
async def sync_watcher_now(watcher_id: str):
    """Executes a manual 'Sync Now' check immediately through the persistent engine."""
    existing = WatcherRepository.get_watcher(watcher_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Watcher not found")

    result = await WatcherService.sync_watcher(watcher_id, is_manual=True)
    return result


@router.post("/{watcher_id}/pause")
async def pause_watcher(watcher_id: str):
    """Pauses scheduled checks for this watcher."""
    success = WatcherRepository.set_watcher_status(watcher_id, "PAUSED")
    if not success:
        raise HTTPException(status_code=404, detail="Watcher not found")
    return {"status": "success", "watcher_id": watcher_id, "state": "PAUSED"}


@router.post("/{watcher_id}/resume")
async def resume_watcher(watcher_id: str):
    """Resumes scheduled checks for this watcher."""
    success = WatcherRepository.set_watcher_status(watcher_id, "ACTIVE")
    if not success:
        raise HTTPException(status_code=404, detail="Watcher not found")
    return {"status": "success", "watcher_id": watcher_id, "state": "ACTIVE"}


@router.get("/{watcher_id}/runs", response_model=List[WatcherRunModel])
async def get_watcher_runs(watcher_id: str, limit: int = Query(20, ge=1, le=100)):
    """Retrieves sync operation audit history for a watcher."""
    runs = WatcherRepository.get_recent_runs(watcher_id, limit=limit)
    return [WatcherRunModel(**r) for r in runs]
