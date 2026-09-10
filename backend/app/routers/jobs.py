import asyncio
import json
from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse
from app.models.schemas import CancelResponse, JobListResponse, JobResponse, JobStatus
from app.services.job_manager import job_manager
from app.utils.errors import JobNotFoundError
from app.utils.logger import logger

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


@router.get("", response_model=JobListResponse)
async def list_jobs_endpoint() -> JobListResponse:
    """Returns the list of recent jobs and active counts."""
    jobs = job_manager.list_jobs()
    return JobListResponse(
        jobs=jobs,
        total=len(jobs),
        active_count=job_manager.get_active_count(),
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_endpoint(job_id: str) -> JobResponse:
    """Returns status and progress detail for a specific job."""
    try:
        job = job_manager.get_job(job_id)
        return job.to_response()
    except JobNotFoundError:
        raise HTTPException(status_code=404, detail="Download job not found.")


@router.get("/{job_id}/events")
async def get_job_events_endpoint(job_id: str, request: Request):
    """
    Streams real-time job progress and state transitions via Server-Sent Events (SSE).
    """
    try:
        job = job_manager.get_job(job_id)
    except JobNotFoundError:
        raise HTTPException(status_code=404, detail="Download job not found.")

    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    job.listeners.add(queue)

    # Immediately queue the current state snapshot
    try:
        queue.put_nowait(job.to_response().model_dump())
    except asyncio.QueueFull:
        pass

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield {
                        "event": "message",
                        "data": json.dumps(data),
                    }
                    if data.get("status") in (
                        JobStatus.COMPLETED.value,
                        JobStatus.FAILED.value,
                        JobStatus.CANCELLED.value,
                    ):
                        # Send final state and end stream
                        break
                except asyncio.TimeoutError:
                    # Keep-alive comment/ping to prevent client timeout
                    yield {
                        "event": "ping",
                        "data": "keep-alive",
                    }
        except asyncio.CancelledError:
            pass
        finally:
            job.listeners.discard(queue)

    return EventSourceResponse(event_generator())


@router.post("/{job_id}/cancel", response_model=CancelResponse)
async def cancel_job_endpoint(job_id: str) -> CancelResponse:
    """Cancels a running or queued job and terminates its subprocess."""
    try:
        job = await job_manager.cancel_job(job_id)
        return CancelResponse(
            job_id=job.id,
            status=job.status,
            message="Job was cancelled successfully.",
        )
    except JobNotFoundError:
        raise HTTPException(status_code=404, detail="Download job not found.")


@router.delete("/{job_id}")
async def delete_job_endpoint(job_id: str):
    """Deletes job record and any saved media files."""
    try:
        await job_manager.delete_job(job_id)
        return {"status": "success", "message": f"Job {job_id} deleted."}
    except JobNotFoundError:
        raise HTTPException(status_code=404, detail="Download job not found.")
