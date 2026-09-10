from pathlib import Path
import pytest
from app.services.file_service import FileService
from app.utils.errors import ValidationError


def test_sanitize_normal_filename():
    name = "Great_Video_2026.mp4"
    assert FileService.sanitize_filename(name) == "Great_Video_2026.mp4"


def test_sanitize_removes_path_traversal():
    traversal_names = [
        "../../etc/passwd",
        "..\\..\\windows\\system32",
        "../../../media.mp4",
        "folder/subfolder/file.mp4",
    ]
    for n in traversal_names:
        clean = FileService.sanitize_filename(n)
        assert ".." not in clean
        assert "/" not in clean
        assert "\\" not in clean


def test_sanitize_removes_illegal_characters():
    name = 'My:Special*Video?"<Cool>|File.mp4'
    clean = FileService.sanitize_filename(name)
    assert not any(c in clean for c in [':', '*', '?', '"', '<', '>', '|'])
    assert clean.endswith(".mp4")


def test_sanitize_truncates_long_names():
    very_long = "a" * 300 + ".mp4"
    clean = FileService.sanitize_filename(very_long, max_length=100)
    assert len(clean) <= 100
    assert clean.endswith(".mp4")


def test_empty_filename_fallback():
    assert FileService.sanitize_filename("") == "media_download"
    assert FileService.sanitize_filename(None) == "media_download"
    assert FileService.sanitize_filename("   ...  ") == "media_download"


def test_safe_file_path_containment(tmp_path):
    base = tmp_path / "downloads"
    base.mkdir()

    safe = FileService.get_safe_file_path(base, "video.mp4")
    assert safe == (base / "video.mp4").resolve()


def test_format_bytes():
    assert FileService.format_bytes(0) == "0 B"
    assert FileService.format_bytes(1024) == "1.0 KB"
    assert FileService.format_bytes(1048576) == "1.0 MB"
    assert FileService.format_bytes(1073741824) == "1.0 GB"
