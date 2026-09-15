from unittest.mock import AsyncMock, patch
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.models.schemas import AnalyzeResponse, VideoQualityOption
from app.repositories.media_repository import MediaRepository


@pytest.mark.asyncio
async def test_preflight_analysis():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Pre-seed an existing item in library to test duplicate identification in preflight
        MediaRepository.add_media({
            "title": "Existing Lesson 1",
            "filename": "lesson1.mp4",
            "relative_path": "lesson1.mp4",
            "source_url": "https://example.com/playlist/lesson1",
            "container": "mp4",
            "resolution": "720p",
            "filesize": 1024 * 1024 * 50,
        })

        mock_analysis = AnalyzeResponse(
            url="https://example.com/playlist/full",
            webpage_url="https://example.com/playlist/full",
            extractor="youtube",
            title="Course Collection",
            media_type="playlist",
            is_playlist=True,
            playlist_id="PL_COURSE",
            entry_count=3,
            entries=[
                {"id": "c1", "title": "Existing Lesson 1", "url": "https://example.com/playlist/lesson1", "duration": 300},
                {"id": "c2", "title": "New Lesson 2", "url": "https://example.com/playlist/lesson2", "duration": 450},
                {"id": "c3", "title": "New Lesson 3", "url": "https://example.com/playlist/lesson3", "duration": 600},
            ],
            video_options=[VideoQualityOption(label="1080p", resolution="1080p", ext="mp4")],
            audio_options=[],
            supported_containers=["mp4"],
            technical_summary={"resolution_str": "1080p", "media_type": "playlist", "format_count": 1},
        )

        with patch("app.services.yt_dlp.YtDlpService.analyze_url", new=AsyncMock(return_value=mock_analysis)):
            payload = {
                "url": "https://example.com/playlist/full",
                "profile_id": "recommended",
                "dry_run": True,
            }
            res = await ac.post("/api/preflight", json=payload)
            assert res.status_code == 200
            data = res.json()
            assert data["total_items"] == 3
            assert data["selected_items"] == 3
            # lesson 1 matches existing media
            assert data["existing_items_count"] + data["upgrade_items_count"] >= 1
            assert data["new_items_count"] == 2
            assert data["storage_status"] in ["sufficient", "warning"]
            assert data["estimated_total_bytes"] > 0
            assert len(data["items"]) == 3
            assert len(data["explanations"]) >= 1
