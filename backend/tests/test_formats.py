from pathlib import Path
from app.services.yt_dlp import YtDlpService, format_duration


def test_format_duration():
    assert format_duration(None) is None
    assert format_duration(45) == "00:45"
    assert format_duration(125) == "02:05"
    assert format_duration(3665) == "01:01:05"


def test_normalize_metadata_parses_formats():
    fake_raw = {
        "title": "Open Source Sample",
        "thumbnail": "https://example.com/thumb.jpg",
        "duration": 180,
        "uploader": "Test Channel",
        "extractor": "youtube",
        "formats": [
            {"format_id": "1", "height": 1080, "vcodec": "avc1", "acodec": "none"},
            {"format_id": "2", "height": 720, "vcodec": "avc1", "acodec": "none"},
            {"format_id": "3", "height": 480, "vcodec": "avc1", "acodec": "none"},
            {"format_id": "audio", "height": None, "vcodec": "none", "acodec": "mp4a"},
        ],
    }

    normalized = YtDlpService._normalize_metadata("https://example.com/video", fake_raw)
    assert normalized.title == "Open Source Sample"
    assert normalized.video_available is True
    assert normalized.audio_available is True
    assert normalized.duration_string == "03:00"

    res_labels = [opt.resolution for opt in normalized.video_options]
    assert "best" in res_labels
    assert "1080p" in res_labels
    assert "720p" in res_labels
    assert "480p" in res_labels


def test_build_download_command():
    temp_dir = Path("/tmp/job_123")
    cmd = YtDlpService.build_download_command(
        url="https://example.com/video",
        temp_dir=temp_dir,
        resolution="1080p",
        audio_only=False,
        output_container="mp4",
    )

    assert any("bestvideo[height<=1080]" in arg for arg in cmd)
    assert "--merge-output-format" in cmd
    assert "mp4" in cmd
    assert cmd[-1] == "https://example.com/video"
    assert cmd[-2] == "--"


def test_build_audio_only_command():
    temp_dir = Path("/tmp/job_123")
    cmd = YtDlpService.build_download_command(
        url="https://example.com/music",
        temp_dir=temp_dir,
        audio_only=True,
        audio_format="mp3",
    )

    assert "-x" in cmd
    assert "--audio-format" in cmd
    assert "mp3" in cmd


def test_parse_progress_line():
    line = "[download]  45.5% of ~ 100.00MiB at  10.50MiB/s ETA 00:05"
    info = YtDlpService.parse_progress_line(line)
    assert info is not None
    assert info["progress"] == 45.5
    assert info["speed"] == "10.50MiB/s"
    assert info["eta"] == "00:05"
    assert info["stage"] == "Downloading"
