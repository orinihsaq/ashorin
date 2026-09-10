import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_healthcheck():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert "version" in data


@pytest.mark.asyncio
async def test_get_system():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/system")
        assert res.status_code == 200
        data = res.json()
        assert "ytdlp_version" in data
        assert "app_version" in data
        assert "max_concurrent_downloads" in data


@pytest.mark.asyncio
async def test_analyze_rejects_ssrf():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post("/api/analyze", json={"url": "http://127.0.0.1:8080/secret"})
        assert res.status_code == 403
        data = res.json()
        assert "Access to local or private network" in data["detail"]


@pytest.mark.asyncio
async def test_analyze_rejects_invalid_scheme():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post("/api/analyze", json={"url": "file:///etc/passwd"})
        assert res.status_code == 422


@pytest.mark.asyncio
async def test_download_rejects_ssrf():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post("/api/download", json={"url": "http://169.254.169.254/meta-data"})
        assert res.status_code == 403


@pytest.mark.asyncio
async def test_jobs_api_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create job with valid public domain dummy url (will fail download safely in background, but queues immediately)
        res = await ac.post(
            "/api/download",
            json={
                "url": "https://example.com/test_video.mp4",
                "resolution": "720p",
                "audio_only": False,
            },
        )
        assert res.status_code == 200
        job_id = res.json()["job_id"]

        # Get job
        res_job = await ac.get(f"/api/jobs/{job_id}")
        assert res_job.status_code == 200
        assert res_job.json()["id"] == job_id

        # Cancel job
        res_cancel = await ac.post(f"/api/jobs/{job_id}/cancel")
        assert res_cancel.status_code == 200

        # List jobs
        res_list = await ac.get("/api/jobs")
        assert res_list.status_code == 200
        assert res_list.json()["total"] >= 1
