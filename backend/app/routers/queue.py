from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    JobListResponse,
    JobResponse,
    QueuePriorityRequest,
    QueueReorderRequest,
    ScheduleDownloadRequest,
)
from app.repositories.job_repository import JobRepository
from app.services.job_manager import job_manager
from app.services.queue_service import QueueService

router = APIRouter(prefix="/api/queue", tags=["Queue"])


@router.get("", response_model=JobListResponse)
async def get_queue():
    """Returns the persistent download queue ordered by priority and queue order."""
    all_jobs = job_manager.list_jobs()
    return JobListResponse(
        jobs=all_jobs,
        total=len(all_jobs),
        active_count=job_manager.get_active_count(),
    )


@router.post("/reorder")
async def reorder_queue(req: QueueReorderRequest):
    """Reorders pending jobs in the queue."""
    QueueService.reorder_queue(req.job_ids)
    return {"status": "success", "message": "Queue reordered successfully."}


@router.post("/{job_id}/priority")
async def set_job_priority(job_id: str, req: QueuePriorityRequest):
    """Updates priority of a job (HIGH, NORMAL, LOW)."""
    success = QueueService.set_job_priority(job_id, req.priority)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        job = job_manager.get_job(job_id)
        job.priority = req.priority.upper()
        job.emit_event()
    except Exception:
        pass
    return {"status": "success", "priority": req.priority.upper()}


@router.post("/{job_id}/retry", response_model=JobResponse)
async def retry_job(job_id: str):
    """Restarts a failed or cancelled job."""
    try:
        job = await job_manager.retry_job(job_id)
        return job.to_response()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{job_id}/schedule")
async def schedule_job(job_id: str, req: ScheduleDownloadRequest):
    """Schedules a job for future execution."""
    success = QueueService.schedule_job(job_id, req.scheduled_for, req.schedule_type)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        job = job_manager.get_job(job_id)
        job.scheduled_for = req.scheduled_for
        job.schedule_type = req.schedule_type
        job.current_stage = "Scheduled"
        job.emit_event()
    except Exception:
        pass
    return {"status": "success", "message": "Job scheduled successfully."}


@router.delete("/completed")
async def clear_completed_jobs():
    """Removes finished (COMPLETED, FAILED, CANCELLED) jobs from the queue."""
    all_jobs = job_manager.list_jobs()
    removed = 0
    for j in all_jobs:
        if j.status in ("COMPLETED", "FAILED", "CANCELLED"):
            try:
                await job_manager.delete_job(j.id)
                removed += 1
            except Exception:
                pass
    return {"status": "success", "removed_count": removed}
