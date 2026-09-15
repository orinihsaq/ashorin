import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.models.job import Job
from app.models.schemas import JobStatus
from app.services.file_service import FileService
from app.services.job_manager import job_manager


client = TestClient(app)


def test_build_content_disposition_unicode_safe():
    header = FileService.build_content_disposition("01 - Test — Special “Quote” & 日本語.mp4")
    assert 'filename="01 - Test _ Special _Quote_ & ___.mp4"' in header
    assert "filename*=UTF-8''01%20-%20Test%20%E2%80%94%20Special%20%E2%80%9CQuote%E2%80%9D%20&%20%E6%97%A5%E6%9C%AC%E8%AA%9E.mp4" in header
    # Header MUST encode cleanly in latin-1 without raising UnicodeEncodeError
    header.encode("latin-1")


def test_get_media_type_detection():
    assert FileService.get_media_type("video.mp4") == "video/mp4"
    assert FileService.get_media_type("movie.mkv") == "video/x-matroska"
    assert FileService.get_media_type("song.mp3") == "audio/mpeg"
    assert FileService.get_media_type("archive.zip") == "application/zip"


def test_download_file_endpoint_valid_and_range(tmp_path):
    settings.download_path.mkdir(parents=True, exist_ok=True)
    test_file = settings.download_path / "test_media_file.mp4"
    test_file.write_bytes(b"A" * 1024)

    job = Job(
        id="job_download_test",
        url="https://example.com/watch?v=test",
        title="Test Media File",
        status=JobStatus.COMPLETED,
        output_filename="test_media_file.mp4",
        output_path=test_file,
    )
    job_manager._jobs[job.id] = job

    # Full GET request
    res = client.get(f"/api/files/{job.id}")
    assert res.status_code == 200
    assert res.headers["content-type"] == "video/mp4"
    assert "attachment;" in res.headers["content-disposition"]
    assert res.content == b"A" * 1024

    # HEAD request
    res_head = client.head(f"/api/files/{job.id}")
    assert res_head.status_code == 200
    assert res_head.headers["content-type"] == "video/mp4"

    # Range request
    res_range = client.get(f"/api/files/{job.id}", headers={"Range": "bytes=0-9"})
    assert res_range.status_code == 206
    assert res_range.content == b"A" * 10
    assert "bytes 0-9/1024" in res_range.headers["content-range"]


def test_download_file_endpoint_errors():
    # Non-existent job
    res_404 = client.get("/api/files/non_existent_id")
    assert res_404.status_code == 404

    # Incomplete job
    job = Job(
        id="job_incomplete",
        url="https://example.com/test",
        status=JobStatus.DOWNLOADING,
    )
    job_manager._jobs[job.id] = job
    res_400 = client.get(f"/api/files/{job.id}")
    assert res_400.status_code == 400


def test_download_playlist_individual_items(tmp_path):
    playlist_dir = settings.download_path / "Test_Playlist"
    playlist_dir.mkdir(parents=True, exist_ok=True)

    v1 = playlist_dir / "01 - Intro.mp4"
    v1.write_bytes(b"VIDEO1_DATA")
    v2 = playlist_dir / "02 - Lessons.mp4"
    v2.write_bytes(b"VIDEO2_DATA")

    job = Job(
        id="playlist_job_test",
        url="https://example.com/playlist?list=123",
        title="Test Playlist",
        is_playlist=True,
        playlist_title="Test Playlist",
        status=JobStatus.COMPLETED,
        output_path=playlist_dir,
    )
    job_manager._jobs[job.id] = job

    # Download by 1-based index
    res1 = client.get(f"/api/files/{job.id}/1")
    assert res1.status_code == 200
    assert res1.content == b"VIDEO1_DATA"
    assert "01 - Intro.mp4" in res1.headers["content-disposition"]

    res2 = client.get(f"/api/files/{job.id}/2")
    assert res2.status_code == 200
    assert res2.content == b"VIDEO2_DATA"

    # Download by exact filename
    res_name = client.get(f"/api/files/{job.id}/01%20-%20Intro.mp4")
    assert res_name.status_code == 200
    assert res_name.content == b"VIDEO1_DATA"

    # Index out of range
    res_out = client.get(f"/api/files/{job.id}/99")
    assert res_out.status_code == 404

    # Path traversal attack blocked
    res_trav = client.get(f"/api/files/{job.id}/..%2F..%2Fetc%2Fpasswd")
    assert res_trav.status_code in (403, 404)
