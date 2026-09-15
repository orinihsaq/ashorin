import os
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.config import settings
from app.main import app
from app.models.job import Job
from app.models.schemas import JobStatus
from app.services.cleanup import CleanupService
from app.services.job_manager import job_manager
from app.services.settings_service import settings_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_retention_settings(tmp_path):
    # Point DOWNLOAD_DIR and TEMP_DIR to temporary directory for isolation
    orig_download_path = settings.DOWNLOAD_DIR
    orig_temp_path = settings.TEMP_DIR
    settings.DOWNLOAD_DIR = str(tmp_path / "downloads")
    settings.TEMP_DIR = str(tmp_path / "temp")
    Path(settings.DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.TEMP_DIR).mkdir(parents=True, exist_ok=True)

    # Reset in-memory settings service
    settings_service._retention_enabled = False
    settings_service._retention_days = 7
    settings_service._initialized = True

    yield

    settings.DOWNLOAD_DIR = orig_download_path
    settings.TEMP_DIR = orig_temp_path
    settings_service._retention_enabled = False
    settings_service._retention_days = 7


def test_retention_disabled_by_default():
    """Verify retention is disabled by default and old files are preserved."""
    download_dir = Path(settings.DOWNLOAD_DIR)
    old_file = download_dir / "old_video.mp4"
    old_file.write_text("dummy video content")

    # Set mtime to 30 days ago
    thirty_days_ago = time.time() - (30 * 86400)
    os.utime(str(old_file), (thirty_days_ago, thirty_days_ago))

    # Run cleanup
    assert settings_service.retention_enabled is False
    deleted = CleanupService.cleanup_downloads()

    assert deleted == 0
    assert old_file.exists()


def test_retention_7_days():
    """Verify 7-day retention deletes 8-day-old file but preserves 6-day-old file."""
    download_dir = Path(settings.DOWNLOAD_DIR)
    now = time.time()

    file_8d = download_dir / "video_8d.mp4"
    file_8d.write_text("old content")
    os.utime(str(file_8d), (now - 8 * 86400, now - 8 * 86400))

    file_6d = download_dir / "video_6d.mp4"
    file_6d.write_text("newer content")
    os.utime(str(file_6d), (now - 6 * 86400, now - 6 * 86400))

    settings_service.update_settings(retention_enabled=True, retention_days=7)
    deleted = CleanupService.cleanup_downloads()

    assert deleted == 1
    assert not file_8d.exists()
    assert file_6d.exists()


def test_retention_14_21_30_days():
    """Verify retention thresholds for 14, 21, and 30 days."""
    download_dir = Path(settings.DOWNLOAD_DIR)
    now = time.time()

    for days in (14, 21, 30):
        # Create expired and non-expired file
        expired = download_dir / f"test_{days}_expired.mp4"
        retained = download_dir / f"test_{days}_retained.mp4"

        expired.write_text("content")
        retained.write_text("content")

        os.utime(str(expired), (now - (days + 1) * 86400, now - (days + 1) * 86400))
        os.utime(str(retained), (now - (days - 1) * 86400, now - (days - 1) * 86400))

        settings_service.update_settings(retention_enabled=True, retention_days=days)
        deleted = CleanupService.cleanup_downloads()

        assert not expired.exists()
        assert retained.exists()
        retained.unlink()


def test_active_download_is_never_deleted():
    """Active downloads must never be cleaned up regardless of age."""
    download_dir = Path(settings.DOWNLOAD_DIR)
    now = time.time()

    active_file = download_dir / "active_download.mp4"
    active_file.write_text("active content")
    os.utime(str(active_file), (now - 50 * 86400, now - 50 * 86400))

    # Register fake active job owning active_file
    active_job = Job(
        id="active_test_job",
        url="https://example.com/test",
        status=JobStatus.DOWNLOADING,
        output_path=active_file,
    )
    job_manager._jobs["active_test_job"] = active_job

    try:
        settings_service.update_settings(retention_enabled=True, retention_days=7)
        deleted = CleanupService.cleanup_downloads()

        assert deleted == 0
        assert active_file.exists()
    finally:
        job_manager._jobs.pop("active_test_job", None)


def test_playlist_folder_retention_and_empty_pruning():
    """Playlist folder items are cleaned and empty playlist folder is removed with metadata."""
    download_dir = Path(settings.DOWNLOAD_DIR)
    now = time.time()

    playlist_dir = download_dir / "My Test Playlist"
    playlist_dir.mkdir()

    v1 = playlist_dir / "01 - Item.mp4"
    v1.write_text("video 1")
    os.utime(str(v1), (now - 10 * 86400, now - 10 * 86400))

    meta = playlist_dir / "playlist.json"
    meta.write_text('{"title": "My Test Playlist"}')

    settings_service.update_settings(retention_enabled=True, retention_days=7)
    deleted = CleanupService.cleanup_downloads()

    assert deleted == 1
    # Both the video and the playlist.json are gone, and empty folder is removed
    assert not v1.exists()
    assert not meta.exists()
    assert not playlist_dir.exists()


def test_playlist_folder_retained_if_unexpired_items_remain():
    """Playlist folder is preserved if some items are not yet expired."""
    download_dir = Path(settings.DOWNLOAD_DIR)
    now = time.time()

    playlist_dir = download_dir / "Partial Playlist"
    playlist_dir.mkdir()

    old_v = playlist_dir / "01 - Old.mp4"
    old_v.write_text("old")
    os.utime(str(old_v), (now - 10 * 86400, now - 10 * 86400))

    new_v = playlist_dir / "02 - New.mp4"
    new_v.write_text("new")
    os.utime(str(new_v), (now - 2 * 86400, now - 2 * 86400))

    meta = playlist_dir / "playlist.json"
    meta.write_text('{"title": "Partial Playlist"}')

    settings_service.update_settings(retention_enabled=True, retention_days=7)
    deleted = CleanupService.cleanup_downloads()

    assert deleted == 1
    assert not old_v.exists()
    assert new_v.exists()
    assert meta.exists()
    assert playlist_dir.exists()


def test_symlink_escape_attempt_protected(tmp_path):
    """Cleanup must never follow symlinks pointing outside DOWNLOAD_DIR."""
    download_dir = Path(settings.DOWNLOAD_DIR)
    external_dir = tmp_path / "external_system_files"
    external_dir.mkdir()

    external_file = external_dir / "critical_data.txt"
    external_file.write_text("do not delete")
    now = time.time()
    os.utime(str(external_file), (now - 100 * 86400, now - 100 * 86400))

    # Create symlink inside download_dir pointing to external_file
    rogue_symlink = download_dir / "symlink_escape"
    try:
        rogue_symlink.symlink_to(external_file)
    except OSError:
        pytest.skip("Symlinks not supported in test environment")

    settings_service.update_settings(retention_enabled=True, retention_days=7)
    CleanupService.cleanup_downloads()

    # External file must still exist unharmed
    assert external_file.exists()
    assert external_file.read_text() == "do not delete"


def test_settings_api_endpoints():
    """Verify GET and PATCH /api/settings."""
    # GET settings
    res = client.get("/api/settings")
    assert res.status_code == 200
    data = res.json()
    assert "retention_enabled" in data
    assert "retention_days" in data
    assert data["allowed_retention_days"] == [7, 14, 21, 30]

    # PATCH valid settings
    res = client.patch("/api/settings", json={"retention_enabled": True, "retention_days": 14})
    assert res.status_code == 200
    updated = res.json()
    assert updated["retention_enabled"] is True
    assert updated["retention_days"] == 14

    # PATCH invalid retention_days (must be 7, 14, 21, or 30)
    res = client.patch("/api/settings", json={"retention_days": 10})
    assert res.status_code == 422

    res = client.patch("/api/settings", json={"retention_days": 5})
    assert res.status_code == 422

    res = client.patch("/api/settings", json={"retention_days": 45})
    assert res.status_code == 422
