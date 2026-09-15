import os
import shutil
import tempfile
import zipfile
from pathlib import Path
import pytest
from app.models.schemas import DownloadConfig, DownloadRequest, JobStatus
from app.services.file_service import FileService
from app.services.job_manager import JobManager
from app.services.yt_dlp import YtDlpService


def test_normalize_playlist_metadata():
    raw_data = {
        "_type": "playlist",
        "id": "PLtest123",
        "title": "Ambient Coding Beats",
        "uploader": "Lofi Producer",
        "entries": [
            {
                "id": "vid1",
                "title": "Night Coding",
                "duration": 180,
                "uploader": "Lofi Producer",
                "thumbnails": [{"url": "https://example.com/thumb1.jpg"}],
                "url": "https://www.youtube.com/watch?v=vid1",
            },
            {
                "id": "vid2",
                "title": "Midnight Rain",
                "duration": 240,
                "uploader": "Lofi Producer",
                "thumbnails": [{"url": "https://example.com/thumb2.jpg"}],
                "url": "https://www.youtube.com/watch?v=vid2",
            },
        ],
    }

    result = YtDlpService._normalize_metadata("https://youtube.com/playlist?list=PLtest123", raw_data)

    assert result.is_playlist is True
    assert result.playlist_id == "PLtest123"
    assert result.title == "Ambient Coding Beats"
    assert result.entry_count == 2
    assert len(result.entries) == 2
    assert result.entries[0].id == "vid1"
    assert result.entries[0].title == "Night Coding"
    assert result.entries[0].duration == 180
    assert result.entries[0].duration_string == "03:00"
    assert result.entries[0].thumbnail == "https://example.com/thumb1.jpg"
    assert result.entries[1].index == 2
    assert len(result.video_options) > 0
    assert len(result.audio_options) > 0


def test_build_playlist_download_command_with_range():
    temp_dir = Path("/tmp/test_playlist_dir")
    config = DownloadConfig(
        playlist_mode="range",
        playlist_start=1,
        playlist_end=5,
        quality="1080p",
    )

    cmd = YtDlpService.build_download_command(
        url="https://youtube.com/playlist?list=PLtest123",
        temp_dir=temp_dir,
        config=config,
    )

    assert "--yes-playlist" in cmd
    assert "--ignore-errors" in cmd
    assert "--playlist-items" in cmd
    items_idx = cmd.index("--playlist-items")
    assert cmd[items_idx + 1] == "1-5"
    assert "--no-playlist" not in cmd


def test_build_playlist_download_command_with_selected_indices():
    temp_dir = Path("/tmp/test_playlist_dir")
    config = DownloadConfig(
        playlist_mode="selected",
        selected_indices=[1, 3, 7, 2],
        audio_mode="audio_only",
        audio_format="mp3",
    )

    cmd = YtDlpService.build_download_command(
        url="https://youtube.com/playlist?list=PLtest123",
        temp_dir=temp_dir,
        config=config,
    )

    assert "--yes-playlist" in cmd
    assert "--ignore-errors" in cmd
    assert "-x" in cmd
    assert "--audio-format" in cmd
    assert "--playlist-items" in cmd
    items_idx = cmd.index("--playlist-items")
    # Should be sorted and deduplicated: 1,2,3,7
    assert cmd[items_idx + 1] == "1,2,3,7"


def test_sanitize_playlist_dir_name():
    assert FileService.sanitize_playlist_dir_name("My Cool / Playlist: Vol. 1") == "My Cool _ Playlist_ Vol. 1"
    # Prevent traversal
    assert ".." not in FileService.sanitize_playlist_dir_name("../../../etc/passwd")
    # Windows reserved words
    assert FileService.sanitize_playlist_dir_name("CON") == "Playlist_CON"
    assert FileService.sanitize_playlist_dir_name("AUX") == "Playlist_AUX"
    # Fallback on empty
    assert FileService.sanitize_playlist_dir_name("") == "Playlist"
    assert FileService.sanitize_playlist_dir_name("   ") == "Playlist"


def test_create_playlist_zip():
    with tempfile.TemporaryDirectory() as tmpdir:
        src_dir = Path(tmpdir) / "test_album"
        src_dir.mkdir()

        # Create sample downloaded media files
        (src_dir / "01 - Track 1.mp3").write_text("audio content 1")
        (src_dir / "02 - Track 2.mp3").write_text("audio content 2")
        # Incomplete part file that MUST be ignored
        (src_dir / "03 - Track 3.mp3.part").write_text("incomplete part")

        zip_out = Path(tmpdir) / "output.zip"
        FileService.create_playlist_zip(src_dir, zip_out)

        assert zip_out.exists()
        with zipfile.ZipFile(zip_out, "r") as zf:
            namelist = zf.namelist()
            assert "01 - Track 1.mp3" in namelist
            assert "02 - Track 2.mp3" in namelist
            assert "03 - Track 3.mp3.part" not in namelist


def test_parse_progress_line_playlist():
    # Item start
    res1 = YtDlpService.parse_progress_line("[download] Downloading item 3 of 20")
    assert res1 is not None
    assert res1["type"] == "playlist_item_start"
    assert res1["item_index"] == 3
    assert res1["total_items"] == 20

    # Playlist title
    res2 = YtDlpService.parse_progress_line("[download] Downloading playlist: Best of Synthwave")
    assert res2 is not None
    assert res2["type"] == "playlist_start"
    assert res2["playlist_title"] == "Best of Synthwave"

    # Destination
    res3 = YtDlpService.parse_progress_line("[download] Destination: /tmp/04 - Neon Lights.mp4")
    assert res3 is not None
    assert res3["type"] == "destination"
    assert res3["item_title"] == "Neon Lights"

    # Item completion
    res4 = YtDlpService.parse_progress_line("[download] 100% of 45.20MiB in 00:03")
    assert res4 is not None
    assert res4["type"] == "item_downloaded"
    assert res4["progress"] == 100.0


@pytest.mark.asyncio
async def test_playlist_cancellation_preserves_completed_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = JobManager()
        req = DownloadRequest(
            url="https://youtube.com/playlist?list=PLtest",
            title="Preserve Test",
            config=DownloadConfig(playlist_mode="all"),
        )
        job = await manager.create_job(req)
        assert job.is_playlist is True

        # Simulate job having a run dir with completed and partial files
        run_dir = Path(tmpdir) / "playlist_run"
        run_dir.mkdir()
        (run_dir / "01 - Song One.mp4").write_text("finished")
        (run_dir / "02 - Song Two.mp4.part").write_text("unfinished")

        job.temp_dir = run_dir
        job.status = JobStatus.DOWNLOADING

        # Cancel job
        await manager.cancel_job(job.id)

        assert job.status == JobStatus.CANCELLED
        # Completed file is preserved!
        assert (run_dir / "01 - Song One.mp4").exists()
        # Incomplete file is purged!
        assert not (run_dir / "02 - Song Two.mp4.part").exists()
        assert job.completed_items == 1
