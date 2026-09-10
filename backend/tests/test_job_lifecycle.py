import asyncio
import pytest
from app.models.schemas import DownloadRequest, JobStatus
from app.services.job_manager import JobManager


@pytest.mark.asyncio
async def test_job_creation():
    mgr = JobManager()
    req = DownloadRequest(
        url="https://example.com/test",
        title="Test Title",
        resolution="720p",
        audio_only=False,
    )
    job = await mgr.create_job(req)

    assert job.id is not None
    assert job.url == req.url
    assert job.title == req.title
    assert job.status == JobStatus.QUEUED

    retrieved = mgr.get_job(job.id)
    assert retrieved.id == job.id


@pytest.mark.asyncio
async def test_job_listing_and_counts():
    mgr = JobManager()
    req1 = DownloadRequest(url="https://example.com/v1")
    req2 = DownloadRequest(url="https://example.com/v2")

    await mgr.create_job(req1)
    await mgr.create_job(req2)

    jobs = mgr.list_jobs()
    assert len(jobs) == 2
    assert mgr.get_active_count() >= 0
