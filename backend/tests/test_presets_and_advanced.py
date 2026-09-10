import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import DownloadConfig, DownloadRequest
from app.services.file_service import FileService
from app.services.presets import PresetService
from app.services.yt_dlp import YtDlpService

client = TestClient(app)


def test_get_presets_endpoint():
    response = client.get("/api/presets")
    assert response.status_code == 200
    data = response.json()
    assert "presets" in data
    assert "default_preset" in data
    assert data["default_preset"] == "recommended"
    
    preset_ids = [p["id"] for p in data["presets"]]
    assert "recommended" in preset_ids
    assert "best_quality" in preset_ids
    assert "audio_only" in preset_ids
    assert "small_file" in preset_ids
    assert "archive" in preset_ids

    # Check structure of a preset
    rec = next(p for p in data["presets"] if p["id"] == "recommended")
    assert rec["name"] == "Recommended"
    assert "description" in rec
    assert "badge" in rec
    assert "config" in rec
    assert rec["config"]["preset"] == "recommended"


def test_sanitize_filename_template():
    # Safe templates
    assert FileService.sanitize_filename_template("%(title)s.%(ext)s") == "%(title)s.%(ext)s"
    assert FileService.sanitize_filename_template("%(uploader)s - %(title)s") == "%(uploader)s - %(title)s"
    
    # Path traversal attempts
    assert ".." not in FileService.sanitize_filename_template("../../etc/passwd")
    assert "/" not in FileService.sanitize_filename_template("foo/bar/baz")
    assert "\\" not in FileService.sanitize_filename_template("foo\\bar\\baz")
    
    # Absolute path / illegal characters
    cleaned = FileService.sanitize_filename_template("/root/secrets/%(title)s:*?<>|")
    assert not cleaned.startswith("/")
    for char in [":", "*", "?", "<", ">", "|"]:
        assert char not in cleaned
        
    # Empty fallback
    assert FileService.sanitize_filename_template("") == "%(title).150B.%(ext)s"
    assert FileService.sanitize_filename_template("   ") == "%(title).150B.%(ext)s"


def test_download_config_backward_compatibility():
    # Legacy request without explicit config
    req = DownloadRequest(
        url="https://youtube.com/watch?v=dQw4w9WgXcQ",
        resolution="1080p",
        output_container="mp4",
        audio_only=False
    )
    resolved = req.get_resolved_config()
    assert resolved.quality == "1080p"
    assert resolved.output_container == "mp4"
    assert resolved.audio_mode == "merge"
    assert resolved.preset == "recommended"

    # Explicit config overriding legacy fields
    cfg = DownloadConfig(
        preset="archive",
        quality="1080p",
        output_container="mkv",
        embed_subtitles=True,
        subtitles=True,
        subtitle_langs="en,es",
        embed_metadata=True,
        write_chapters=True,
        retries=10,
        concurrent_fragments=4,
    )
    req2 = DownloadRequest(
        url="https://youtube.com/watch?v=dQw4w9WgXcQ",
        config=cfg
    )
    resolved2 = req2.get_resolved_config()
    assert resolved2.preset == "archive"
    assert resolved2.output_container == "mkv"
    assert resolved2.embed_subtitles is True
    assert resolved2.retries == 10
    assert resolved2.concurrent_fragments == 4


def test_build_download_command_with_advanced_config(tmp_path):
    output_dir = tmp_path / "test_out"
    output_dir.mkdir()
    
    config = DownloadConfig(
        preset="custom",
        quality="1080p",
        output_container="mkv",
        audio_mode="merge",
        subtitles=True,
        embed_subtitles=True,
        subtitle_langs="en,fr",
        auto_subtitles=True,
        embed_metadata=True,
        write_chapters=True,
        embed_thumbnail=True,
        retries=5,
        concurrent_fragments=3,
        timeout=45,
    )
    
    cmd = YtDlpService.build_download_command(
        url="https://example.com/watch?v=12345",
        temp_dir=output_dir,
        config=config,
    )
    
    assert cmd[0] == YtDlpService.get_binary_path()
    assert "--merge-output-format" in cmd
    assert cmd[cmd.index("--merge-output-format") + 1] == "mkv"
    assert "--embed-subs" in cmd
    assert "--sub-langs" in cmd
    assert cmd[cmd.index("--sub-langs") + 1] == "en,fr"
    assert "--write-auto-subs" in cmd
    assert "--embed-metadata" in cmd
    assert "--embed-chapters" in cmd
    assert "--embed-thumbnail" in cmd
    assert "--retries" in cmd
    assert cmd[cmd.index("--retries") + 1] == "5"
    assert "--concurrent-fragments" in cmd
    assert cmd[cmd.index("--concurrent-fragments") + 1] == "3"
    assert "--socket-timeout" in cmd
    assert cmd[cmd.index("--socket-timeout") + 1] == "45"
    # Ensure `--` safe delimiter is right before URL
    assert cmd[-2] == "--"
    assert cmd[-1] == "https://example.com/watch?v=12345"


def test_system_info_contains_storage_metrics():
    response = client.get("/api/system")
    assert response.status_code == 200
    data = response.json()
    assert "storage_info" in data
    storage = data["storage_info"]
    assert "total_bytes" in storage
    assert "used_bytes" in storage
    assert "free_bytes" in storage
    assert "percent_used" in storage
    assert "free_formatted" in storage
    assert "total_formatted" in storage
