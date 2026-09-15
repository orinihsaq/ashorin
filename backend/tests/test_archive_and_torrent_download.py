import io
import os
import time
import zipfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.models.job import Job
from app.models.schemas import JobStatus
from app.services.archive_service import ArchiveService
from app.services.job_manager import job_manager

client = TestClient(app)


def test_torrent_single_file_download(tmp_path):
    settings.download_path.mkdir(parents=True, exist_ok=True)
    torrent_folder = settings.download_path / "Single_Torrent_Folder"
    torrent_folder.mkdir(parents=True, exist_ok=True)
    single_file = torrent_folder / "Ubuntu.iso"
    payload = b"ISO_IMAGE_SINGLE_FILE_PAYLOAD_BYTES"
    single_file.write_bytes(payload)

    job = Job(
        id="tor_single_job",
        url="magnet:?xt=urn:btih:abcdef1234567890abcdef1234567890abcdef12&dn=Ubuntu",
        title="Ubuntu",
        provider="torrent",
        status=JobStatus.COMPLETED,
        output_path=single_file,
        output_filename="Ubuntu.iso",
        output_type="file",
        file_count=1,
    )
    job_manager._jobs[job.id] = job

    # Standard /api/files endpoint
    res = client.get(f"/api/files/{job.id}")
    assert res.status_code == 200
    assert "Ubuntu.iso" in res.headers["content-disposition"]
    assert res.headers["content-type"] != "application/zip"
    assert res.content == payload

    # Convenience /api/torrents endpoint
    res_tor = client.get(f"/api/torrents/{job.id}/download")
    assert res_tor.status_code == 200
    assert "Ubuntu.iso" in res_tor.headers["content-disposition"]
    assert res_tor.content == payload


def test_torrent_multi_file_zip_download(tmp_path):
    settings.download_path.mkdir(parents=True, exist_ok=True)
    settings.archive_path.mkdir(parents=True, exist_ok=True)

    album_dir = settings.download_path / "Awesome_Album_2026"
    album_dir.mkdir(parents=True, exist_ok=True)
    sub_dir = album_dir / "CD2"
    sub_dir.mkdir(parents=True, exist_ok=True)

    f1 = album_dir / "01_track.flac"
    f1.write_bytes(b"FLAC_DATA_TRACK_1")
    f2 = album_dir / "02_track.flac"
    f2.write_bytes(b"FLAC_DATA_TRACK_2")
    f3 = sub_dir / "03_track.flac"
    f3.write_bytes(b"FLAC_DATA_TRACK_3")
    cover = album_dir / "cover.jpg"
    cover.write_bytes(b"JPEG_COVER_ART")

    # Temporary/partial torrent file that MUST be excluded from the zip
    part_file = album_dir / "incomplete.part"
    part_file.write_bytes(b"PARTIAL")

    job = Job(
        id="tor_multi_job",
        url="magnet:?xt=urn:btih:1111222233334444555566667777888899990000&dn=AwesomeAlbum",
        title="Awesome Album",
        provider="torrent",
        status=JobStatus.COMPLETED,
        output_path=album_dir,
        output_filename="Awesome_Album.zip",
        output_type="directory",
        file_count=4,
    )
    job_manager._jobs[job.id] = job

    res = client.get(f"/api/files/{job.id}")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/zip"
    assert "Awesome_Album.zip" in res.headers["content-disposition"]

    # Validate ZIP integrity and top-level folder preservation (Section 12)
    zf = zipfile.ZipFile(io.BytesIO(res.content))
    names = zf.namelist()
    assert any("Awesome_Album_2026" in n and n.endswith("01_track.flac") for n in names)
    assert any("Awesome_Album_2026" in n and n.endswith("02_track.flac") for n in names)
    assert any("Awesome_Album_2026" in n and ("CD2/03_track.flac" in n or "CD2\\03_track.flac" in n) for n in names)
    assert any("Awesome_Album_2026" in n and n.endswith("cover.jpg") for n in names)
    assert not any(n.endswith(".part") for n in names)

    # Source files remain completely untouched (Section 30 item 11)
    assert f1.exists() and f1.read_bytes() == b"FLAC_DATA_TRACK_1"
    assert cover.exists() and cover.read_bytes() == b"JPEG_COVER_ART"


def test_torrent_nested_folders_hierarchy(tmp_path):
    settings.download_path.mkdir(parents=True, exist_ok=True)
    torrent_root = settings.download_path / "My_Series_Pack"
    torrent_root.mkdir(parents=True, exist_ok=True)

    (torrent_root / "Videos").mkdir(parents=True, exist_ok=True)
    (torrent_root / "Subtitles").mkdir(parents=True, exist_ok=True)
    (torrent_root / "Extras").mkdir(parents=True, exist_ok=True)

    (torrent_root / "Videos" / "a.mp4").write_bytes(b"VIDEO_A")
    (torrent_root / "Videos" / "b.mp4").write_bytes(b"VIDEO_B")
    (torrent_root / "Subtitles" / "en.srt").write_bytes(b"SUBTITLES")
    (torrent_root / "Extras" / "cover.jpg").write_bytes(b"COVER")

    job = Job(
        id="tor_nested_job",
        url="magnet:?xt=urn:btih:3333444455556666777788889999000011112222&dn=Series",
        title="My Series Pack",
        provider="torrent",
        status=JobStatus.COMPLETED,
        output_path=torrent_root,
        output_filename="My_Series_Pack.zip",
        output_type="directory",
        file_count=4,
    )
    job_manager._jobs[job.id] = job

    res = client.get(f"/api/torrents/{job.id}/download")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/zip"

    zf = zipfile.ZipFile(io.BytesIO(res.content))
    names = zf.namelist()
    assert any("My_Series_Pack" in n and "Videos" in n and n.endswith("a.mp4") for n in names)
    assert any("My_Series_Pack" in n and "Videos" in n and n.endswith("b.mp4") for n in names)
    assert any("My_Series_Pack" in n and "Subtitles" in n and n.endswith("en.srt") for n in names)
    assert any("My_Series_Pack" in n and "Extras" in n and n.endswith("cover.jpg") for n in names)


def test_torrent_download_while_seeding(tmp_path):
    settings.download_path.mkdir(parents=True, exist_ok=True)
    seed_file = settings.download_path / "seeding_media.mp4"
    seed_file.write_bytes(b"SEEDING_VIDEO_BYTES")

    job = Job(
        id="tor_seeding_job",
        url="magnet:?xt=urn:btih:aabbccddeeff00112233445566778899aabbccdd&dn=SeedingTest",
        title="Seeding Test",
        provider="torrent",
        status=JobStatus.SEEDING,
        output_path=seed_file,
        output_filename="seeding_media.mp4",
        output_type="file",
    )
    job_manager._jobs[job.id] = job

    res = client.get(f"/api/files/{job.id}")
    assert res.status_code == 200
    assert res.content == b"SEEDING_VIDEO_BYTES"


def test_torrent_empty_directory_error_409(tmp_path):
    settings.download_path.mkdir(parents=True, exist_ok=True)
    empty_dir = settings.download_path / "Empty_Torrent_Folder"
    empty_dir.mkdir(parents=True, exist_ok=True)

    job = Job(
        id="tor_empty_job",
        url="magnet:?xt=urn:btih:5555666677778888999900001111222233334444&dn=EmptyTorrent",
        title="Empty Torrent",
        provider="torrent",
        status=JobStatus.COMPLETED,
        output_path=empty_dir,
        output_type="directory",
        file_count=0,
    )
    job_manager._jobs[job.id] = job

    res = client.get(f"/api/files/{job.id}")
    assert res.status_code == 409
    assert res.headers["content-type"].startswith("application/json")
    data = res.json()
    assert "error" in data
    assert data["error"]["code"] == "TORRENT_OUTPUT_EMPTY"


def test_torrent_missing_output_error_404(tmp_path):
    missing_path = settings.download_path / "DoesNotExistNonExistent"

    job = Job(
        id="tor_missing_job",
        url="magnet:?xt=urn:btih:7777888899990000111122223333444455556666&dn=MissingTorrent",
        title="Missing Torrent",
        provider="torrent",
        status=JobStatus.COMPLETED,
        output_path=missing_path,
        output_type="directory",
    )
    job_manager._jobs[job.id] = job

    res = client.get(f"/api/files/{job.id}")
    assert res.status_code == 404
    assert res.headers["content-type"].startswith("application/json")
    data = res.json()
    assert "error" in data
    assert data["error"]["code"] == "TORRENT_OUTPUT_NOT_FOUND"


def test_torrent_path_traversal_rejected():
    traversal_path = Path("/etc")

    job = Job(
        id="tor_traversal_job",
        url="magnet:?xt=urn:btih:8888999900001111222233334444555566667777&dn=Traversal",
        title="Traversal Test",
        provider="torrent",
        status=JobStatus.COMPLETED,
        output_path=traversal_path,
        output_type="directory",
    )
    job_manager._jobs[job.id] = job

    res = client.get(f"/api/files/{job.id}")
    assert res.status_code == 403


def test_torrent_symlink_escape_protection(tmp_path):
    settings.download_path.mkdir(parents=True, exist_ok=True)
    outside_dir = tmp_path / "outside_secret"
    outside_dir.mkdir(parents=True, exist_ok=True)
    secret_file = outside_dir / "secret.key"
    secret_file.write_text("CONFIDENTIAL")

    safe_dir = settings.download_path / "Symlink_Test_Dir"
    safe_dir.mkdir(parents=True, exist_ok=True)
    (safe_dir / "legit.txt").write_text("OK")

    symlink_file = safe_dir / "escaped_link.txt"
    try:
        symlink_file.symlink_to(secret_file)
    except OSError:
        pytest.skip("Symlinks not supported on this OS/filesystem")

    archive_path = ArchiveService.create_torrent_zip(safe_dir, "sym_test.zip", "sym_job")
    zf = zipfile.ZipFile(archive_path)
    names = zf.namelist()
    assert any(n.endswith("legit.txt") for n in names)
    assert not any(n.endswith("escaped_link.txt") for n in names)


def test_torrent_archive_metadata_endpoint(tmp_path):
    settings.download_path.mkdir(parents=True, exist_ok=True)
    target_dir = settings.download_path / "Meta_Archive_Test"
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "f1.txt").write_bytes(b"ABC")
    (target_dir / "f2.txt").write_bytes(b"DEF")

    job = Job(
        id="tor_meta_job",
        url="magnet:?xt=urn:btih:9999000011112222333344445555666677778888&dn=MetaTest",
        title="Meta Test",
        provider="torrent",
        status=JobStatus.COMPLETED,
        output_path=target_dir,
        output_filename="Meta_Test.zip",
        output_type="directory",
        file_count=2,
    )
    job_manager._jobs[job.id] = job

    res = client.post(f"/api/torrents/{job.id}/archive")
    assert res.status_code == 200
    data = res.json()
    assert data["archive_name"] == "Meta_Test.zip"
    assert data["file_count"] == 2
    assert data["archive_size"] > 0
    assert "archive_path" in data


def test_archive_cache_invalidation_on_change(tmp_path):
    settings.download_path.mkdir(parents=True, exist_ok=True)
    test_dir = settings.download_path / "Cache_Invalidate_Dir"
    test_dir.mkdir(parents=True, exist_ok=True)
    file1 = test_dir / "file1.txt"
    file1.write_bytes(b"version 1")

    job_id = "cache_invalidation_job"
    zip1 = ArchiveService.create_torrent_zip(test_dir, "test.zip", job_id)
    zf1 = zipfile.ZipFile(zip1)
    entry_name1 = next(n for n in zf1.namelist() if n.endswith("file1.txt"))
    assert zf1.read(entry_name1) == b"version 1"

    # Update file content and update mtime to future
    time.sleep(0.05)
    file1.write_bytes(b"version 2 updated")
    future_time = time.time() + 10
    os.utime(file1, (future_time, future_time))

    # Second call should invalidate old cache and generate fresh archive
    zip2 = ArchiveService.create_torrent_zip(test_dir, "test.zip", job_id)
    zf2 = zipfile.ZipFile(zip2)
    entry_name2 = next(n for n in zf2.namelist() if n.endswith("file1.txt"))
    assert zf2.read(entry_name2) == b"version 2 updated"


def test_archive_cleanup_stale():
    settings.archive_path.mkdir(parents=True, exist_ok=True)
    old_archive = settings.archive_path / "job_old_archive.zip"
    old_archive.write_bytes(b"OLD_ZIP")
    past_time = time.time() - 7200
    os.utime(old_archive, (past_time, past_time))

    fresh_archive = settings.archive_path / "job_fresh_archive.zip"
    fresh_archive.write_bytes(b"FRESH_ZIP")

    cleaned = ArchiveService.cleanup_stale_archives(max_age_seconds=900)
    assert cleaned >= 1
    assert not old_archive.exists()
    assert fresh_archive.exists()

    fresh_archive.unlink(missing_ok=True)
