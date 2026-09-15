import asyncio
import io
import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path
import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.db.database import get_db, init_db
from app.main import app
from app.models.schemas import DownloadRequest, JobStatus, TorrentDownloadConfig
from app.repositories.job_repository import JobRepository
from app.repositories.media_repository import MediaRepository
from app.repositories.torrent_repository import TorrentRepository
from app.services.cleanup import CleanupService
from app.services.duplicate_detector import DuplicateDetector
from app.services.job_manager import job_manager
from app.services.providers import get_provider
from app.services.torrent.bencode import bencode_decode, bencode_encode, parse_torrent_bytes
from app.services.torrent.detector import InputDetector
from app.services.torrent.engine import MockTorrentEngine, TorrentStatus, get_torrent_engine
from app.services.torrent.magnet import MagnetParser
from app.services.torrent.torrent_service import torrent_service
from app.utils.errors import ValidationError, StorageFullError, FileTooLargeError


# Helper to generate a minimal valid .torrent file in memory
def make_sample_torrent_bytes(name="test_torrent_sample", files=None, length=1024 * 1024):
    if files is None:
        info_dict = {
            b"name": name.encode("utf-8"),
            b"piece length": 32768,
            b"pieces": b"A" * 20 * 32,  # 32 pieces of 20-byte SHA1 hashes
            b"length": length,
        }
    else:
        info_dict = {
            b"name": name.encode("utf-8"),
            b"piece length": 32768,
            b"pieces": b"A" * 20 * 32,
            b"files": [
                {
                    b"path": [part.encode("utf-8") for part in f["path"].split("/")],
                    b"length": f["size"],
                }
                for f in files
            ],
        }

    torrent_dict = {
        b"announce": b"http://tracker.example.com:80/announce",
        b"comment": b"ashoriN test torrent",
        b"creation date": int(time.time()),
        b"info": info_dict,
    }
    return bencode_encode(torrent_dict)


def test_bencode_primitives():
    # Integer
    assert bencode_decode(b"i42e") == 42
    assert bencode_decode(b"i-123e") == -123
    assert bencode_decode(b"i0e") == 0
    assert bencode_encode(42) == b"i42e"

    # String
    assert bencode_decode(b"4:spam") == b"spam"
    assert bencode_decode(b"0:") == b""
    assert bencode_encode(b"spam") == b"4:spam"
    assert bencode_encode("spam") == b"4:spam"

    # List
    assert bencode_decode(b"l4:spami42ee") == [b"spam", 42]
    assert bencode_encode([b"spam", 42]) == b"l4:spami42ee"

    # Dict
    d = {b"cow": b"moo", b"spam": b"eggs"}
    encoded = bencode_encode(d)
    assert bencode_decode(encoded) == {"cow": b"moo", "spam": b"eggs"}

    # Max depth security check
    deep_str = b"l" * 35 + b"i1e" + b"e" * 35
    with pytest.raises(ValidationError):
        bencode_decode(deep_str)


def test_bencode_parse_torrent():
    t_bytes = make_sample_torrent_bytes(name="my_test_movie.mp4", length=5000000)
    meta = parse_torrent_bytes(t_bytes)
    assert meta["name"] == "my_test_movie.mp4"
    assert meta["total_size"] == 5000000
    assert len(meta["info_hash"]) == 40
    assert meta["is_multi_file"] is False
    assert len(meta["files"]) == 1
    assert meta["files"][0]["size"] == 5000000


def test_bencode_multi_file_torrent():
    files = [
        {"path": "video/movie.mp4", "size": 3000000},
        {"path": "audio/soundtrack.mp3", "size": 1000000},
        {"path": "sample.nfo", "size": 2048},
    ]
    t_bytes = make_sample_torrent_bytes(name="my_media_pack", files=files)
    meta = parse_torrent_bytes(t_bytes)
    assert meta["name"] == "my_media_pack"
    assert meta["is_multi_file"] is True
    assert meta["total_size"] == 4002048
    assert len(meta["files"]) == 3
    assert meta["files"][0]["path"] == "video/movie.mp4"


def test_bencode_path_traversal_rejection():
    # Torrent attempting path traversal in file path
    malicious_files = [
        {"path": "../../etc/passwd", "size": 1024},
    ]
    t_bytes = make_sample_torrent_bytes(name="evil_torrent", files=malicious_files)
    with pytest.raises(ValidationError):
        parse_torrent_bytes(t_bytes)


def test_magnet_parser_hex_and_base32():
    # 40-char hex info hash
    hex_hash = "1234567890abcdef1234567890abcdef12345678"
    uri = f"magnet:?xt=urn:btih:{hex_hash}&dn=Ubuntu+24.04&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337"
    assert MagnetParser.is_magnet_url(uri) is True
    parsed = MagnetParser.parse_magnet(uri)
    assert parsed["info_hash"] == hex_hash.lower()
    assert parsed["name"] == "Ubuntu+24.04"
    assert len(parsed["trackers"]) == 1

    # RFC 4648 Base32 info hash (32 characters) -> Decodes to 40-char hex
    base32_hash = "MFRGGZDFMZTWQ2LKNNWG23TPOBYXE43U"
    b32_uri = f"magnet:?xt=urn:btih:{base32_hash}&dn=Sample+Media"
    parsed_b32 = MagnetParser.parse_magnet(b32_uri)
    assert len(parsed_b32["info_hash"]) == 40
    assert parsed_b32["name"] == "Sample+Media"

    # Invalid scheme
    assert MagnetParser.is_magnet_url("http://example.com/not-magnet") is False
    with pytest.raises(ValidationError):
        MagnetParser.parse_magnet("https://example.com/movie.mp4")

    # Missing btih
    with pytest.raises(ValidationError):
        MagnetParser.parse_magnet("magnet:?dn=NoHashHere")


def test_input_detector():
    # Standard URLs
    assert InputDetector.detect("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "ytdlp"
    assert InputDetector.detect("https://vimeo.com/123456") == "ytdlp"

    # Magnet URIs
    assert InputDetector.detect("magnet:?xt=urn:btih:1234567890abcdef1234567890abcdef12345678") == "torrent_magnet"

    # .torrent files
    assert InputDetector.detect("/tmp/ubuntu.torrent") == "torrent_file"
    assert InputDetector.detect("https://example.com/debian.iso.torrent") == "torrent_file"


def test_provider_registry():
    ytdlp_p = get_provider("ytdlp")
    assert ytdlp_p.provider_name == "ytdlp"

    torrent_p = get_provider("torrent")
    assert torrent_p.provider_name == "torrent"

    with pytest.raises(ValueError):
        get_provider("invalid_unknown_provider")


@pytest.mark.asyncio
async def test_mock_torrent_engine_lifecycle():
    engine = MockTorrentEngine()
    t_bytes = make_sample_torrent_bytes(name="lifecycle_test_tor", length=100000)
    t_file = settings.torrent_metadata_path / "lifecycle.torrent"
    t_file.parent.mkdir(parents=True, exist_ok=True)
    t_file.write_bytes(t_bytes)

    dest_dir = settings.download_path / "mock_download_dir"
    dest_dir.mkdir(parents=True, exist_ok=True)

    ih = engine.add_torrent(str(t_file), dest_dir)
    assert len(ih) == 40

    st = engine.get_status(ih)
    assert st is not None
    assert st.name == "lifecycle_test_tor"
    assert st.progress >= 0.0

    # Test file priorities
    engine.set_file_priorities(ih, {0: "high"})
    assert engine.get_file_priorities(ih)[0] == "high"

    # Test pause & resume
    engine.pause(ih)
    assert engine.get_status(ih).is_paused is True
    engine.resume(ih)
    assert engine.get_status(ih).is_paused is False

    # Test force recheck
    engine.force_recheck(ih)
    assert engine.get_status(ih).state == "checking"

    # Test fastresume data serialization & restoration
    buf = engine.save_resume_data(ih)
    assert buf is not None and len(buf) > 0

    engine.remove(ih, delete_files=False)
    assert engine.get_status(ih) is None

    # Restore from resume data
    ih2 = engine.add_torrent(str(t_file), dest_dir, resume_data=buf)
    assert ih2 == ih
    assert engine.get_status(ih) is not None


@pytest.mark.asyncio
async def test_torrent_job_creation_and_telemetry():
    t_bytes = make_sample_torrent_bytes(name="ashorin_tor_job.mp4", length=204800)
    meta = parse_torrent_bytes(t_bytes)
    ih = meta["info_hash"]

    # Save torrent metadata file
    tor_path = settings.torrent_metadata_path / f"{ih}.torrent"
    tor_path.parent.mkdir(parents=True, exist_ok=True)
    tor_path.write_bytes(t_bytes)

    t_cfg = TorrentDownloadConfig(
        info_hash=ih,
        name="ashorin_tor_job.mp4",
        torrent_file_path=str(tor_path),
        seeding_mode="stop",
    )

    req = DownloadRequest(
        url=f"magnet:?xt=urn:btih:{ih}&dn=ashorin_tor_job.mp4",
        provider="torrent",
        torrent_config=t_cfg,
    )

    job = await job_manager.create_job(req)
    assert job.provider == "torrent"
    assert job.info_hash == ih
    assert job.id is not None

    # Wait for execution step
    await asyncio.sleep(1.2)
    saved_job = job_manager.get_job(job.id)
    assert saved_job.provider == "torrent"
    # Status should have progressed
    assert saved_job.status in (JobStatus.DOWNLOADING, JobStatus.COMPLETED, JobStatus.SEEDING)


@pytest.mark.asyncio
async def test_duplicate_torrent_detection():
    ih = "abcdef1234567890abcdef1234567890abcdef12"
    # Insert a dummy active torrent record
    tor_id = str(uuid.uuid4())
    TorrentRepository.save_torrent({
        "id": tor_id,
        "info_hash": ih,
        "name": "Dup Torrent",
        "status": "DOWNLOADING",
    })

    is_dup, reason, record = DuplicateDetector.check_torrent_duplicate(ih)
    assert is_dup is True
    assert "active" in reason.lower()

    # Different hash is not duplicate
    is_dup2, _, _ = DuplicateDetector.check_torrent_duplicate("9999999999999999999999999999999999999999")
    assert is_dup2 is False


@pytest.mark.asyncio
async def test_retention_protection_for_active_torrent():
    ih = "1111222233334444555566667777888899990000"
    active_tor_dir = settings.download_path / "Protected_Active_Torrent"
    active_tor_dir.mkdir(parents=True, exist_ok=True)
    target_media = active_tor_dir / "protected_movie.mp4"
    target_media.write_bytes(b"content" * 100)

    # Make target_media old so retention would normally delete it
    old_time = time.time() - (86400 * 30)
    os.utime(str(target_media), (old_time, old_time))
    os.utime(str(active_tor_dir), (old_time, old_time))

    # Register in TorrentRepository as SEEDING
    TorrentRepository.save_torrent({
        "id": str(uuid.uuid4()),
        "info_hash": ih,
        "name": "Protected_Active_Torrent",
        "download_dir": str(active_tor_dir),
        "status": "SEEDING",
    })

    # Run cleanup with 1 second retention
    deleted = CleanupService.cleanup_downloads(retention_seconds=1)
    # The active/seeding torrent directory MUST NOT be deleted
    assert target_media.exists() is True
    assert active_tor_dir.exists() is True


@pytest.mark.asyncio
async def test_torrent_api_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. System endpoint reports torrent support
        sys_res = await ac.get("/api/system")
        assert sys_res.status_code == 200
        sys_data = sys_res.json()
        assert sys_data["torrent_enabled"] is True
        assert "torrent_engine" in sys_data
        assert "active_torrents" in sys_data

        # 2. Analyze magnet endpoint
        hex_hash = "aabbccddeeff00112233445566778899aabbccdd"
        mag_uri = f"magnet:?xt=urn:btih:{hex_hash}&dn=Debian+Linux"
        ana_res = await ac.post("/api/analyze", json={"url": mag_uri})
        assert ana_res.status_code == 200
        ana_data = ana_res.json()
        assert ana_data["title"] == "Debian+Linux"
        assert ana_data["torrent_info"] is not None
        assert ana_data["torrent_info"]["info_hash"] == hex_hash

        # 3. Upload .torrent endpoint
        t_bytes = make_sample_torrent_bytes(name="uploaded_distro.iso", length=500000)
        files = {"file": ("uploaded_distro.torrent", t_bytes, "application/x-bittorrent")}
        up_res = await ac.post("/api/torrents/upload", files=files)
        assert up_res.status_code == 200
        up_data = up_res.json()
        assert up_data["name"] == "uploaded_distro.iso"
        assert up_data["total_size"] == 500000
        assert len(up_data["info_hash"]) == 40

        # 4. Filter media library by provider=torrent
        lib_res = await ac.get("/api/library?provider=torrent")
        assert lib_res.status_code == 200
        assert "items" in lib_res.json()


@pytest.mark.asyncio
async def test_interactive_magnet_stops_at_waiting_for_selection():
    """Verifies interactive magnet submission pauses payload and waits for file selection."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        hex_hash = f"11223344556677889900{uuid.uuid4().hex[:20]}"
        mag_uri = f"magnet:?xt=urn:btih:{hex_hash}&dn=InteractiveTestTorrent"

        # Submit interactive download request
        res = await ac.post("/api/download", json={
            "url": mag_uri,
            "provider": "torrent",
            "input_type": "magnet",
            "interactive": True,
        })
        assert res.status_code == 200
        job_id = res.json()["job_id"]

        # Wait briefly for process_torrent_job to run
        await asyncio.sleep(0.5)

        # Check job status
        job_res = await ac.get(f"/api/jobs/{job_id}")
        assert job_res.status_code == 200
        job_data = job_res.json()

        # Job must be in WAITING_FOR_SELECTION with 0 downloaded bytes
        assert job_data["status"] == "WAITING_FOR_SELECTION"
        assert job_data["downloaded_bytes"] == 0
        assert job_data["interactive"] is True
        assert job_data["torrent_info"] is not None
        assert len(job_data["torrent_info"]["files"]) > 0

        # Now simulate user selecting files and clicking "Start Download"
        start_res = await ac.post(f"/api/torrents/{job_id}/start", json={
            "selected_files": [0],
            "file_priorities": {"0": "high"},
            "destination_folder": "MyCustomFolder",
            "seeding_mode": "ratio_1",
        })
        assert start_res.status_code == 200
        started_data = start_res.json()
        assert started_data["status"] == "DOWNLOADING"
        assert started_data["interactive"] is False

        await asyncio.sleep(0.5)

        # Job has now progressed to downloading
        job_res_after = await ac.get(f"/api/jobs/{job_id}")
        assert job_res_after.status_code == 200
        assert job_res_after.json()["status"] in ("DOWNLOADING", "COMPLETED", "SEEDING")


@pytest.mark.asyncio
async def test_background_magnet_auto_starts():
    """Verifies background non-interactive magnet submission auto-starts payload download."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        hex_hash = f"22334455667788990011{uuid.uuid4().hex[:20]}"
        mag_uri = f"magnet:?xt=urn:btih:{hex_hash}&dn=BackgroundTestTorrent"

        # Submit non-interactive download request
        res = await ac.post("/api/download", json={
            "url": mag_uri,
            "provider": "torrent",
            "input_type": "magnet",
            "interactive": False,
        })
        assert res.status_code == 200
        job_id = res.json()["job_id"]

        # Wait briefly for process_torrent_job to run
        await asyncio.sleep(0.5)

        job_res = await ac.get(f"/api/jobs/{job_id}")
        assert job_res.status_code == 200
        # In background mode, it auto-advances to DOWNLOADING
        assert job_res.json()["status"] in ("DOWNLOADING", "COMPLETED", "SEEDING")


@pytest.mark.asyncio
async def test_metadata_received_immediately_extracts_manifest_without_peers_or_dht():
    """Verifies that once metadata is received, manifest is immediately extracted without peer/dht requirements."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        hex_hash = f"33445566778899001122{uuid.uuid4().hex[:20]}"
        mag_uri = f"magnet:?xt=urn:btih:{hex_hash}&dn=FastManifestTorrent"

        # Submit interactive magnet
        res = await ac.post("/api/download", json={
            "url": mag_uri,
            "provider": "torrent",
            "input_type": "magnet",
            "interactive": True,
        })
        assert res.status_code == 200
        job_id = res.json()["job_id"]

        # Wait for metadata resolution loop to complete
        await asyncio.sleep(0.5)

        job_res = await ac.get(f"/api/jobs/{job_id}")
        assert job_res.status_code == 200
        job_data = job_res.json()

        # Must be in WAITING_FOR_SELECTION, NOT stuck in ACQUIRING_METADATA
        assert job_data["status"] == "WAITING_FOR_SELECTION"
        assert job_data["torrent_info"] is not None
        assert job_data["torrent_info"]["has_metadata"] is True
        assert len(job_data["torrent_info"]["files"]) > 0
        assert job_data["torrent_info"]["total_size"] > 0
        assert job_data["torrent_telemetry"]["metadata_phase"] == "Metadata received"

