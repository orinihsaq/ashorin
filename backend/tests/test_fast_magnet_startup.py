import asyncio
import hashlib
import time
import uuid
from pathlib import Path
import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app
from app.models.schemas import DownloadRequest, JobStatus, TorrentDownloadConfig
from app.repositories.job_repository import JobRepository
from app.services.duplicate_detector import DuplicateDetector
from app.services.job_manager import job_manager
from app.services.torrent.engine import MockTorrentEngine
from app.services.torrent.metadata_cache import MetadataCache
from app.services.torrent.torrent_service import torrent_service


def random_sha1() -> str:
    return hashlib.sha1(uuid.uuid4().bytes).hexdigest()


@pytest.fixture(autouse=True)
def ensure_mock_engine():
    """Ensure MockTorrentEngine is active for fast-path tests."""
    engine = MockTorrentEngine()
    torrent_service._engine = engine
    return engine


@pytest.mark.asyncio
async def test_immediate_job_creation_for_magnet():
    """Valid magnet submission to /api/download responds fast (< 100ms) with ACQUIRING_METADATA."""
    transport = ASGITransport(app=app)
    raw_hash = random_sha1()
    magnet_uri = f"magnet:?xt=urn:btih:{raw_hash}&dn=Fast+Startup+Test"

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        t0 = time.perf_counter()
        res = await ac.post(
            "/api/download",
            json={
                "url": magnet_uri,
                "override_duplicate": True,
            },
        )
        duration_ms = (time.perf_counter() - t0) * 1000

        assert res.status_code == 200
        # Verification: must respond fast (< 150ms in test harness)
        assert duration_ms < 150
        data = res.json()
        assert data["job_id"] is not None
        assert data["status"] in (JobStatus.ACQUIRING_METADATA.value, JobStatus.QUEUED.value)
        assert data["provider"] == "torrent"


@pytest.mark.asyncio
async def test_analyze_magnet_non_blocking():
    """POST /api/analyze responds immediately without waiting for peers."""
    transport = ASGITransport(app=app)
    raw_hash = random_sha1()
    magnet_uri = f"magnet:?xt=urn:btih:{raw_hash}&dn=Non+Blocking+Analysis"

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        t0 = time.perf_counter()
        res = await ac.post("/api/analyze", json={"url": magnet_uri})
        duration_ms = (time.perf_counter() - t0) * 1000

        assert res.status_code == 200
        assert duration_ms < 150
        data = res.json()
        assert data["status"] == "metadata_pending"
        assert data["info_hash"] == raw_hash
        assert data["is_torrent"] is True


def test_metadata_cache_lifecycle(tmp_path):
    """MetadataCache safely saves and retrieves metadata, rejects traversal, handles casing."""
    raw_hash = random_sha1()
    sample_meta = {
        "info_hash": raw_hash,
        "name": "Cached Linux ISO",
        "total_size": 1048576000,
        "files": [
            {"index": 0, "path": "linux.iso", "size": 1048576000},
        ],
    }

    # Save
    success = MetadataCache.save(raw_hash, sample_meta)
    assert success is not None
    assert success.exists()

    # Case-insensitive hit
    retrieved = MetadataCache.get(raw_hash.upper())
    assert retrieved is not None
    assert retrieved["name"] == "Cached Linux ISO"
    assert retrieved["total_size"] == 1048576000

    # Path traversal protection
    traversal_meta = MetadataCache.get("../../etc/passwd")
    assert traversal_meta is None

    # Invalid SHA1 length protection
    assert MetadataCache.get("too_short") is None


@pytest.mark.asyncio
async def test_metadata_cache_instant_hit_on_analyze():
    """Cached magnet analysis returns status='ready' and files instantly (< 50ms)."""
    raw_hash = random_sha1()
    MetadataCache.save(
        raw_hash,
        {
            "info_hash": raw_hash,
            "name": "Precached Movie",
            "total_size": 2048,
            "files": [{"index": 0, "path": "movie.mp4", "size": 2048}],
        },
    )

    transport = ASGITransport(app=app)
    mag_uri = f"magnet:?xt=urn:btih:{raw_hash}&dn=Precached+Movie"

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        t0 = time.perf_counter()
        res = await ac.post("/api/analyze", json={"url": mag_uri})
        duration_ms = (time.perf_counter() - t0) * 1000

        assert res.status_code == 200
        assert duration_ms < 50
        data = res.json()
        assert data["status"] == "ready"
        assert data["name"] == "Precached Movie"
        assert len(data["files"]) == 1


@pytest.mark.asyncio
async def test_duplicate_detector_includes_ready_state():
    """DuplicateDetector recognises jobs in READY status as duplicates."""
    raw_hash = random_sha1()
    magnet_uri = f"magnet:?xt=urn:btih:{raw_hash}&dn=Duplicate+Ready+Test"

    # Create job in READY state
    req = DownloadRequest(
        url=magnet_uri,
        title="Duplicate Ready Test",
        provider="torrent",
        input_type="magnet",
        torrent_config=TorrentDownloadConfig(info_hash=raw_hash),
    )
    job = await job_manager.create_job(req)
    job.status = JobStatus.READY
    JobRepository.save_job(job)

    is_dup, reason, rec = DuplicateDetector.check_torrent_duplicate(raw_hash)
    assert is_dup is True
    assert "READY" in reason


@pytest.mark.asyncio
async def test_start_ready_job_transition():
    """Calling start_ready_job transitions job from READY to DOWNLOADING."""
    raw_hash = random_sha1()
    magnet_uri = f"magnet:?xt=urn:btih:{raw_hash}&dn=Ready+Start+Test"

    req = DownloadRequest(
        url=magnet_uri,
        title="Ready Start Test",
        provider="torrent",
        input_type="magnet",
        torrent_config=TorrentDownloadConfig(info_hash=raw_hash, manual_review=True),
    )
    job = await job_manager.create_job(req)
    job.status = JobStatus.READY
    JobRepository.save_job(job)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(f"/api/torrents/{job.id}/start", json={"selected_files": [0]})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == JobStatus.DOWNLOADING.value
