import json
from pathlib import Path
import pytest
from app.config import settings
from app.models.job import Job
from app.models.schemas import DownloadConfig, JobStatus
from app.services.file_service import FileService
from app.services.yt_dlp import YtDlpService


def test_allocate_playlist_dir_initial(tmp_path):
    """Allocates safe initial playlist directory."""
    base = tmp_path / "downloads"
    base.mkdir()

    folder = FileService.allocate_playlist_dir(base, "Best Coding Tutorials")
    assert folder.name == "Best Coding Tutorials"
    assert folder.is_dir()
    assert folder.parent == base


def test_allocate_playlist_dir_collision_resolution(tmp_path):
    """Never overwrites existing downloads; allocates (2), (3) deterministically."""
    base = tmp_path / "downloads"
    base.mkdir()

    # First allocation
    folder1 = FileService.allocate_playlist_dir(base, "Python Mastery")
    assert folder1.name == "Python Mastery"
    # Place a completed file inside folder1 so it is occupied
    (folder1 / "01 - Intro.mp4").write_text("video")

    # Second allocation of the same playlist title
    folder2 = FileService.allocate_playlist_dir(base, "Python Mastery")
    assert folder2.name == "Python Mastery (2)"
    (folder2 / "01 - Intro.mp4").write_text("video")

    # Third allocation
    folder3 = FileService.allocate_playlist_dir(base, "Python Mastery")
    assert folder3.name == "Python Mastery (3)"


def test_allocate_playlist_dir_reuses_empty_directory(tmp_path):
    """Empty directories with no media can be reused safely without collisions."""
    base = tmp_path / "downloads"
    base.mkdir()

    empty_folder = base / "Empty Playlist"
    empty_folder.mkdir()

    folder = FileService.allocate_playlist_dir(base, "Empty Playlist")
    assert folder.name == "Empty Playlist"


def test_write_playlist_metadata(tmp_path):
    """Writes sanitized playlist.json without sensitive tokens."""
    folder = tmp_path / "Sample Playlist"
    folder.mkdir()

    meta_path = FileService.write_playlist_metadata(
        playlist_dir=folder,
        title="Sample Playlist",
        source_url="https://youtube.com/playlist?list=12345",
        item_count=10,
        completed_items=8,
        playlist_id="PL12345",
    )

    assert meta_path.name == "playlist.json"
    assert meta_path.exists()

    data = json.loads(meta_path.read_text(encoding="utf-8"))
    assert data["title"] == "Sample Playlist"
    assert data["item_count"] == 10
    assert data["completed_items"] == 8
    assert data["source_url"] == "https://youtube.com/playlist?list=12345"
    assert "downloaded_at" in data
    # Ensure no secret headers or cookies exist
    assert "cookies" not in data
    assert "token" not in data


def test_playlist_zero_padding_under_and_over_99():
    """Playlist output template uses 02d for <= 99 items and 03d for > 99 items."""
    tmp = Path("/tmp")

    # Case A: <= 99 items (e.g. 25 items)
    cfg_small = DownloadConfig(playlist_mode="playlist")
    cmd_small = YtDlpService.build_download_command(
        url="https://example.com/playlist",
        temp_dir=tmp,
        config=cfg_small,
        total_items=25,
    )
    cmd_str_small = " ".join(cmd_small)
    assert "%(playlist_index)02d" in cmd_str_small
    assert "%(playlist_index)03d" not in cmd_str_small

    # Case B: > 99 items (e.g. 150 items)
    cfg_large = DownloadConfig(playlist_mode="playlist")
    cmd_large = YtDlpService.build_download_command(
        url="https://example.com/playlist",
        temp_dir=tmp,
        config=cfg_large,
        total_items=150,
    )
    cmd_str_large = " ".join(cmd_large)
    assert "%(playlist_index)03d" in cmd_str_large


def test_job_response_file_availability_when_deleted(tmp_path):
    """When a completed download is deleted from disk, is_file_available is False and stage is Automatically removed."""
    orig_download_path = settings.DOWNLOAD_DIR
    settings.DOWNLOAD_DIR = str(tmp_path)

    try:
        # 1. Single file job with missing output file
        missing_file = tmp_path / "deleted_file.mp4"
        single_job = Job(
            id="test_single_del",
            url="https://example.com/video",
            status=JobStatus.COMPLETED,
            output_path=missing_file,
            output_filename="deleted_file.mp4",
        )
        res = single_job.to_response()
        assert res.is_file_available is False
        assert res.download_url is None
        assert res.current_stage == "Automatically removed"

        # 2. Existing file job
        existing_file = tmp_path / "present_file.mp4"
        existing_file.write_text("data")
        present_job = Job(
            id="test_single_present",
            url="https://example.com/video",
            status=JobStatus.COMPLETED,
            output_path=existing_file,
            output_filename="present_file.mp4",
        )
        res_present = present_job.to_response()
        assert res_present.is_file_available is True
        assert res_present.download_url == "/api/files/test_single_present"

        # 3. Playlist job with empty/missing folder
        missing_playlist_dir = tmp_path / "Deleted Playlist"
        playlist_job = Job(
            id="test_playlist_del",
            url="https://example.com/playlist",
            status=JobStatus.COMPLETED,
            is_playlist=True,
            playlist_title="Deleted Playlist",
            output_path=missing_playlist_dir,
        )
        res_pl = playlist_job.to_response()
        assert res_pl.is_file_available is False
        assert res_pl.download_url is None
        assert res_pl.current_stage == "Automatically removed"
    finally:
        settings.DOWNLOAD_DIR = orig_download_path
