import os
import time
from pathlib import Path
from app.config import settings
from app.services.cleanup import CleanupService


def test_cleanup_downloads_expired(tmp_path, monkeypatch):
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    monkeypatch.setattr(settings, "DOWNLOAD_DIR", str(downloads))

    # Create expired file (modified 2 hours ago)
    old_file = downloads / "old_video.mp4"
    old_file.write_text("dummy video")
    two_hours_ago = time.time() - 7200
    os.utime(old_file, (two_hours_ago, two_hours_ago))

    # Create fresh file (modified 1 minute ago)
    fresh_file = downloads / "new_video.mp4"
    fresh_file.write_text("fresh video")

    # Run cleanup with 1 hour (3600s) retention
    deleted = CleanupService.cleanup_downloads(3600)
    assert deleted == 1
    assert not old_file.exists()
    assert fresh_file.exists()


def test_cleanup_disabled_when_zero(tmp_path, monkeypatch):
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    monkeypatch.setattr(settings, "DOWNLOAD_DIR", str(downloads))

    old_file = downloads / "video.mp4"
    old_file.write_text("data")
    long_ago = time.time() - 999999
    os.utime(old_file, (long_ago, long_ago))

    # 0 retention means disabled
    deleted = CleanupService.cleanup_downloads(0)
    assert deleted == 0
    assert old_file.exists()
