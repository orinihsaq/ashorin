import pytest
from httpx import ASGITransport, AsyncClient
from app.config import settings
from app.main import app
from app.repositories.api_key_repository import ApiKeyRepository
from app.repositories.media_repository import MediaRepository


@pytest.mark.asyncio
async def test_queue_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Get queue
        res = await ac.get("/api/queue")
        assert res.status_code == 200
        data = res.json()
        assert "jobs" in data
        assert "active_count" in data

        # 2. Clear completed jobs
        res = await ac.delete("/api/queue/completed")
        assert res.status_code == 200
        assert "removed_count" in res.json()


@pytest.mark.asyncio
async def test_batch_import_deduplication():
    import uuid
    uid = uuid.uuid4().hex[:8]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        batch_payload = {
            "urls": [
                f"https://example.com/batch_{uid}_1?utm_source=twitter",
                f"https://example.com/batch_{uid}_1?utm_source=facebook",  # Same after normalization
                f"https://example.com/batch_{uid}_2",
                "invalid-url-schema",
            ],
            "priority": "HIGH",
        }
        res = await ac.post("/api/batch/queue", json=batch_payload)
        assert res.status_code == 200
        data = res.json()
        assert data["total_submitted"] == 4
        assert data["duplicates_skipped"] >= 1
        assert data["invalid_urls"] >= 1
        assert data["total_accepted"] >= 1


@pytest.mark.asyncio
async def test_media_library_and_streaming():
    # Seed a media item
    test_file = settings.download_path / "stream_test_video.mp4"
    test_file.write_bytes(b"A" * 1024 * 100)  # 100KB dummy video

    media_id = MediaRepository.add_media({
        "title": "Stream Test Video",
        "filename": test_file.name,
        "relative_path": test_file.name,
        "source_url": "https://example.com/stream-test",
        "container": "mp4",
        "filesize": len(test_file.read_bytes()),
    })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # List library
        res = await ac.get("/api/library")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1

        # Toggle favorite
        res = await ac.post(f"/api/library/{media_id}/favorite")
        assert res.status_code == 200
        assert res.json()["is_favorite"] is True

        # Toggle protect
        res = await ac.post(f"/api/library/{media_id}/protect")
        assert res.status_code == 200
        assert res.json()["is_protected"] is True

        # Delete while protected should fail with 400
        res = await ac.delete(f"/api/library/{media_id}")
        assert res.status_code == 400

        # Full stream request
        res = await ac.get(f"/api/media/{media_id}/stream")
        assert res.status_code == 200
        assert res.headers["accept-ranges"] == "bytes"

        # Partial stream request (HTTP 206 Range)
        res = await ac.get(f"/api/media/{media_id}/stream", headers={"Range": "bytes=0-1023"})
        assert res.status_code == 206
        assert res.headers["content-range"].startswith("bytes 0-1023/")
        assert len(res.content) == 1024

        # Clean up
        MediaRepository.toggle_protected(media_id)
        res = await ac.delete(f"/api/library/{media_id}")
        assert res.status_code == 200


@pytest.mark.asyncio
async def test_public_automation_v1_api():
    # 1. Create an API key
    raw_key, record = ApiKeyRepository.create_key("V1 Test Client")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Attempt submission without header -> 401
        res = await ac.post("/api/v1/jobs", json={"url": "https://example.com/v1-test"})
        assert res.status_code == 401

        # Attempt with invalid key -> 401
        res = await ac.post(
            "/api/v1/jobs",
            json={"url": "https://example.com/v1-test"},
            headers={"X-API-Key": "ash_live_invalid_123456789"},
        )
        assert res.status_code == 401

        # Submit with valid key -> 200
        res = await ac.post(
            "/api/v1/jobs",
            json={"url": "https://example.com/v1-test"},
            headers={"X-API-Key": raw_key},
        )
        assert res.status_code == 200
        data = res.json()
        assert "job_id" in data
        job_id = data["job_id"]

        # Query job with valid key -> 200
        res = await ac.get(f"/api/v1/jobs/{job_id}", headers={"X-API-Key": raw_key})
        assert res.status_code == 200
        assert res.json()["id"] == job_id

        # Cancel job -> 200
        res = await ac.delete(f"/api/v1/jobs/{job_id}", headers={"X-API-Key": raw_key})
        assert res.status_code == 200

    ApiKeyRepository.delete_key(record["id"])


@pytest.mark.asyncio
async def test_webhook_security_and_management():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # SSRF check: private IP should be rejected with 400
        res = await ac.post(
            "/api/webhooks",
            json={"url": "http://192.168.1.1/hook", "events": ["job.completed"]},
        )
        assert res.status_code == 400

        # Valid public webhook URL
        res = await ac.post(
            "/api/webhooks",
            json={"url": "https://httpbin.org/post", "events": ["job.completed"]},
        )
        assert res.status_code == 200
        wh_data = res.json()
        wid = wh_data["id"]

        # List webhooks
        res = await ac.get("/api/webhooks")
        assert res.status_code == 200
        assert any(w["id"] == wid for w in res.json())

        # Test ping
        res = await ac.post(f"/api/webhooks/{wid}/test")
        assert res.status_code == 200

        # Delete webhook
        res = await ac.delete(f"/api/webhooks/{wid}")
        assert res.status_code == 200


@pytest.mark.asyncio
async def test_statistics_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/statistics")
        assert res.status_code == 200
        data = res.json()
        assert "total_downloads" in data
        assert "completed_downloads" in data
        assert "top_extractors" in data
        assert "top_containers" in data
        assert "downloads_by_day" in data
