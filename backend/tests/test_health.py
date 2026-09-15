from pathlib import Path
import pytest
from httpx import ASGITransport, AsyncClient
from app.config import settings
from app.main import app
from app.repositories.health_repository import HealthRepository
from app.repositories.media_repository import MediaRepository
from app.services.health_service import HealthService


@pytest.mark.asyncio
async def test_media_health_scan_and_repair():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Create artificial test artifacts:
        # a) Abandoned incomplete file (.part)
        part_file = settings.download_path / "temp_artifact_test.mp4.part"
        part_file.write_bytes(b"X" * 1024 * 5)

        # b) Orphan file (not in library)
        orphan_file = settings.download_path / "orphan_song_test.mp3"
        orphan_file.write_bytes(b"Y" * 1024 * 10)

        # c) Missing file record (in db, but file deleted)
        missing_id = MediaRepository.add_media({
            "title": "Missing File Video",
            "filename": "missing_video_123.mp4",
            "relative_path": "missing_video_123.mp4",
            "source_url": "https://example.com/missing123",
            "container": "mp4",
            "filesize": 1024 * 100,
            "is_protected": False,
        })

        # 2. Trigger Health Scan
        res = await ac.post("/api/health/scan")
        assert res.status_code == 200
        scan = res.json()
        assert scan["status"] == "COMPLETED"
        assert scan["issues_found"] >= 2

        # 3. Query Issues
        res = await ac.get("/api/health/issues")
        assert res.status_code == 200
        issues = res.json()
        types = {i["issue_type"] for i in issues}
        assert "incomplete_download" in types or "orphaned_record" in types or "missing_file" in types

        # 4. Safe Repair
        res = await ac.post("/api/health/repair", json={"repair_type": "clean_incomplete"})
        assert res.status_code == 200
        assert res.json()["status"] == "success"
        # .part file should be deleted
        assert not part_file.exists()

        # Re-index orphans
        res = await ac.post("/api/health/repair", json={"repair_type": "reindex_orphans"})
        assert res.status_code == 200

        # Remove missing files from database
        res = await ac.post("/api/health/repair", json={"repair_type": "remove_stale"})
        assert res.status_code == 200
        assert MediaRepository.get_media(missing_id) is None

        # Clean up orphan file
        orphan_file.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_storage_forecast():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/health/forecast")
        assert res.status_code == 200
        data = res.json()
        assert "percent_used" in data
        assert "daily_download_rate_formatted" in data
        assert "status_summary" in data
