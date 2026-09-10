import asyncio
from pathlib import Path
import pytest
from app.models.job import Job
from app.models.schemas import DownloadRequest, JobStatus
from app.services.job_manager import JobManager


@pytest.mark.asyncio
async def test_job_cancellation(tmp_path):
    mgr = JobManager()
    req = DownloadRequest(url="https://example.com/long_video")
    job = await mgr.create_job(req)

    temp_dir = tmp_path / "temp_job"
    temp_dir.mkdir()
    job.temp_dir = temp_dir

    # Cancel the job
    cancelled = await mgr.cancel_job(job.id)
    assert cancelled.status == JobStatus.CANCELLED
    assert cancelled.is_cancelled is True


@pytest.mark.asyncio
async def test_cancelling_already_completed_is_noop():
    mgr = JobManager()
    req = DownloadRequest(url="https://example.com/done")
    job = await mgr.create_job(req)
    job.status = JobStatus.COMPLETED

    res = await mgr.cancel_job(job.id)
    assert res.status == JobStatus.COMPLETED
