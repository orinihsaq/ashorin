from pathlib import Path
import pytest
from app.config import settings
from app.repositories.media_repository import MediaRepository
from app.repositories.quality_repository import QualityRepository
from app.services.quality_service import QualityService


def test_resolution_parsing():
    assert QualityService.parse_resolution_height("1080p") == 1080
    assert QualityService.parse_resolution_height("4k") == 2160
    assert QualityService.parse_resolution_height("720p") == 720
    assert QualityService.parse_resolution_height("1920x1080") == 1080
    assert QualityService.parse_resolution_height("invalid") == 0


def test_quality_upgrade_detection():
    # 720p vs 1080p -> upgrade
    is_better, reason = QualityService.is_upgrade("720p", "1080p")
    assert is_better is True
    assert "1080p" in reason

    # 1080p vs 720p -> not upgrade
    is_better, _ = QualityService.is_upgrade("1080p", "720p")
    assert is_better is False

    # Same resolution but higher FPS -> upgrade
    is_better, reason = QualityService.is_upgrade("1080p", "1080p", current_fps=30, available_fps=60)
    assert is_better is True
    assert "60fps" in reason


def test_storage_impact_calculation():
    diff, summary = QualityService.calculate_storage_impact(100 * 1024 * 1024, 250 * 1024 * 1024)
    assert diff == 150 * 1024 * 1024
    assert "+150.0 MB" in summary

    diff_red, summary_red = QualityService.calculate_storage_impact(200 * 1024 * 1024, 150 * 1024 * 1024)
    assert diff_red == -50 * 1024 * 1024
    assert "-50.0 MB" in summary_red


@pytest.mark.asyncio
async def test_safe_upgrade_execution():
    # 1. Seed initial media item (720p)
    old_file = settings.download_path / "upgrade_test_initial.mp4"
    old_file.write_bytes(b"A" * 1024 * 10)  # 10KB

    media_id = MediaRepository.add_media({
        "title": "Upgrade Test Video",
        "filename": old_file.name,
        "relative_path": old_file.name,
        "source_url": "https://example.com/upgrade_test",
        "container": "mp4",
        "resolution": "720p",
        "filesize": old_file.stat().st_size,
    })

    # Register target
    QualityRepository.upsert_target({
        "media_id": media_id,
        "current_height": 720,
        "target_quality": "1080p",
        "minimum_quality": "720p",
        "upgrade_policy": "ask",
    })

    # 2. Check and register upgrade availability
    has_upgrade = QualityService.check_and_register_upgrade(
        media_id=media_id,
        new_res="1080p",
        new_filesize=1024 * 25,
        source_url="https://example.com/upgrade_test",
    )
    assert has_upgrade is True

    avail = QualityRepository.list_available_upgrades()
    assert any(u["media_id"] == media_id for u in avail)

    # 3. Create upgraded file (1080p)
    new_file = settings.download_path / "upgrade_test_new_1080p.mp4"
    new_file.write_bytes(b"B" * 1024 * 25)  # 25KB

    # 4. Apply safe upgrade
    success = await QualityService.apply_safe_upgrade(media_id, "job_upg_1", new_file)
    assert success is True

    # 5. Verify old file was safely removed and new file is active in library
    assert not old_file.exists()
    assert new_file.exists()

    updated_media = MediaRepository.get_media(media_id)
    assert updated_media["filename"] == new_file.name
    assert updated_media["filesize"] == 1024 * 25

    # Clean up
    new_file.unlink(missing_ok=True)
