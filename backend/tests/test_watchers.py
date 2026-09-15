from unittest.mock import AsyncMock, patch
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.models.schemas import AnalyzeResponse, VideoQualityOption
from app.repositories.watcher_repository import WatcherRepository
from app.services.watcher_service import WatcherService


@pytest.mark.asyncio
async def test_watchers_crud_and_status():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Create watcher
        payload = {
            "name": "Synthwave Collection",
            "source_url": "https://www.youtube.com/playlist?list=PL_TEST_123",
            "source_type": "playlist",
            "schedule": "every_6_hours",
            "profile_id": "recommended",
            "target_quality": "1080p",
            "minimum_quality": "720p",
            "upgrade_policy": "ask",
            "duplicate_policy": "skip",
            "download_new": True,
        }
        res = await ac.post("/api/watchers", json=payload)
        assert res.status_code == 200
        data = res.json()
        watcher_id = data["id"]
        assert data["name"] == "Synthwave Collection"
        assert data["status"] == "ACTIVE"
        assert data["interval_seconds"] == 21600

        # 2. Get watcher
        res = await ac.get(f"/api/watchers/{watcher_id}")
        assert res.status_code == 200
        assert res.json()["id"] == watcher_id

        # 3. Pause and resume
        res = await ac.post(f"/api/watchers/{watcher_id}/pause")
        assert res.status_code == 200
        assert res.json()["state"] == "PAUSED"

        res = await ac.post(f"/api/watchers/{watcher_id}/resume")
        assert res.status_code == 200
        assert res.json()["state"] == "ACTIVE"

        # 4. Update watcher
        res = await ac.patch(f"/api/watchers/{watcher_id}", json={"name": "Renamed Synthwave"})
        assert res.status_code == 200
        assert res.json()["name"] == "Renamed Synthwave"

        # 5. List watchers
        res = await ac.get("/api/watchers")
        assert res.status_code == 200
        assert any(w["id"] == watcher_id for w in res.json())

        # 6. Delete watcher
        res = await ac.delete(f"/api/watchers/{watcher_id}")
        assert res.status_code == 200


@pytest.mark.asyncio
async def test_watcher_sync_execution():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create a watcher
        payload = {
            "name": "Sync Execution Test",
            "source_url": "https://www.youtube.com/playlist?list=PL_MOCK_SYNC",
            "schedule": "hourly",
            "profile_id": "recommended",
            "download_new": False,  # Dry sync
        }
        res = await ac.post("/api/watchers", json=payload)
        watcher_id = res.json()["id"]

        # Mock analyze_url to simulate discovering 2 items
        mock_analysis = AnalyzeResponse(
            url="https://www.youtube.com/playlist?list=PL_MOCK_SYNC",
            webpage_url="https://www.youtube.com/playlist?list=PL_MOCK_SYNC",
            extractor="youtube",
            title="Mock Playlist",
            media_type="playlist",
            is_playlist=True,
            playlist_id="PL_MOCK_SYNC",
            entry_count=2,
            entries=[
                {"id": "mock1", "title": "Track 1", "url": "https://www.youtube.com/watch?v=mock1", "duration": 180},
                {"id": "mock2", "title": "Track 2", "url": "https://www.youtube.com/watch?v=mock2", "duration": 240},
            ],
            video_options=[VideoQualityOption(label="1080p", resolution="1080p", ext="mp4")],
            audio_options=[],
            supported_containers=["mp4"],
            technical_summary={"resolution_str": "1080p", "media_type": "playlist", "format_count": 2},
        )

        with patch("app.services.yt_dlp.YtDlpService.analyze_url", new=AsyncMock(return_value=mock_analysis)):
            res = await ac.post(f"/api/watchers/{watcher_id}/sync")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "success"
            assert data["items_seen"] == 2

            # Overlap check: while syncing, second invocation returns skipped
            WatcherService._active_sync_ids.add(watcher_id)
            res_overlap = await ac.post(f"/api/watchers/{watcher_id}/sync")
            assert res_overlap.status_code == 200
            assert res_overlap.json()["status"] == "skipped"
            WatcherService._active_sync_ids.discard(watcher_id)

        # Check sync runs
        res = await ac.get(f"/api/watchers/{watcher_id}/runs")
        assert res.status_code == 200
        runs = res.json()
        assert len(runs) >= 1
        assert runs[0]["items_seen"] == 2

        # Clean up
        await ac.delete(f"/api/watchers/{watcher_id}")
