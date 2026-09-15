import pytest
import uuid
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.db.database import get_db, init_db
from app.main import app
from app.models.schemas import DownloadRequest, JobStatus
from app.repositories.api_key_repository import ApiKeyRepository
from app.repositories.job_repository import JobRepository
from app.repositories.torrent_repository import TorrentRepository
from app.services.duplicate_detector import DuplicateDetector
from app.services.security import SecurityService
from app.services.torrent.detector import InputDetector
from app.services.torrent.engine import map_torrent_error
from app.services.torrent.magnet import MagnetParser
from app.utils.errors import ValidationError, SSRFSecurityError


@pytest.fixture(autouse=True)
def setup_test_environment():
    init_db()


# ---------------------------------------------------------------------------
# 1. Magnet Parsing & Literal '+' Preservation Tests
# ---------------------------------------------------------------------------

def test_minimal_magnet_uri():
    uri = "magnet:?xt=urn:btih:0123456789abcdef0123456789abcdef01234567"
    parsed = MagnetParser.parse_magnet(uri)
    assert parsed["info_hash"] == "0123456789abcdef0123456789abcdef01234567"
    assert parsed["name"] == "magnet_0123456789"
    assert parsed["trackers"] == []
    assert parsed["canonical_uri"] == uri


def test_base32_info_hash_magnet():
    # 32-char base32 string: MFRGGZDFMZTWQ2LKNNWG23TPOBYXE43U
    uri = "magnet:?xt=urn:btih:MFRGGZDFMZTWQ2LKNNWG23TPOBYXE43U&dn=Test+Base32"
    parsed = MagnetParser.parse_magnet(uri)
    assert len(parsed["info_hash"]) == 40
    assert all(c in "0123456789abcdef" for c in parsed["info_hash"])
    assert parsed["name"] == "Test+Base32"


def test_preservation_of_plus_characters():
    # Ensure '+' in query params is NOT converted to spaces ' '
    uri = "magnet:?xt=urn:btih:0123456789abcdef0123456789abcdef01234567&dn=Ubuntu+22.04+LTS&tr=http%3A%2F%2Ftracker.org%2Fannounce%2Btest"
    parsed = MagnetParser.parse_magnet(uri)
    assert "+" in parsed["name"]
    assert parsed["name"] == "Ubuntu+22.04+LTS"
    assert len(parsed["trackers"]) == 1
    assert "+test" in parsed["trackers"][0]


def test_magnet_with_multiple_trackers():
    uri = (
        "magnet:?xt=urn:btih:0123456789abcdef0123456789abcdef01234567"
        "&tr=udp%3A%2F%2Ftracker1.example.com%3A1337%2Fannounce"
        "&tr=udp%3A%2F%2Ftracker2.example.com%3A6969%2Fannounce"
        "&tr=http%3A%2F%2Ftracker3.example.com%2Fannounce"
    )
    parsed = MagnetParser.parse_magnet(uri)
    assert len(parsed["trackers"]) == 3
    assert "udp://tracker1.example.com:1337/announce" in parsed["trackers"]
    assert "udp://tracker2.example.com:6969/announce" in parsed["trackers"]
    assert "http://tracker3.example.com/announce" in parsed["trackers"]


def test_magnet_with_extra_parameters():
    uri = (
        "magnet:?xt=urn:btih:0123456789abcdef0123456789abcdef01234567"
        "&dn=ExtraParams"
        "&xl=104857600"
        "&ws=https%3A%2F%2Fwebseed.example.com%2Ffile.iso"
        "&custom=xyz"
    )
    parsed = MagnetParser.parse_magnet(uri)
    assert parsed["total_size"] == 104857600
    assert parsed["web_seeds"] == ["https://webseed.example.com/file.iso"]
    assert parsed["canonical_uri"] == uri


# ---------------------------------------------------------------------------
# 2. Section 23 Validation Error Messages
# ---------------------------------------------------------------------------

def test_validation_empty_magnet():
    with pytest.raises(ValidationError, match="Invalid magnet link. The URI is empty."):
        MagnetParser.validate("")

    with pytest.raises(ValidationError, match="Invalid magnet link. The URI is empty."):
        MagnetParser.validate("   ")

    with pytest.raises(ValidationError, match="Invalid magnet link. The URI is empty."):
        MagnetParser.validate("magnet:")


def test_validation_not_magnet():
    with pytest.raises(ValidationError, match="Not a valid magnet URI: must begin with 'magnet:'."):
        MagnetParser.validate("https://example.com/video.mp4")


def test_validation_missing_xt():
    with pytest.raises(ValidationError, match="Invalid magnet link. The link does not contain a valid BitTorrent info hash."):
        MagnetParser.validate("magnet:?dn=MissingXT")


def test_validation_unsupported_urn():
    with pytest.raises(ValidationError, match="Invalid magnet link. The link does not contain a valid BitTorrent info hash."):
        MagnetParser.validate("magnet:?xt=urn:ed2k:31D6CFE0D16AE931B73C59D7E0C089C0")


def test_validation_invalid_hash_length():
    with pytest.raises(ValidationError, match="Invalid magnet link. The link does not contain a valid BitTorrent info hash."):
        MagnetParser.validate("magnet:?xt=urn:btih:1234")


def test_validation_invalid_hash_characters():
    with pytest.raises(ValidationError, match="Invalid magnet link. The link does not contain a valid BitTorrent info hash."):
        MagnetParser.validate("magnet:?xt=urn:btih:ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ")


# ---------------------------------------------------------------------------
# 3. Security Service & Input Routing
# ---------------------------------------------------------------------------

def test_security_service_input_routing():
    # Valid magnet passes SecurityService.validate_url
    mag = "magnet:?xt=urn:btih:0123456789abcdef0123456789abcdef01234567&dn=Safe+Magnet"
    valid_url = SecurityService.validate_url(mag)
    assert valid_url == mag

    # Malformed magnet raises ValidationError through SecurityService
    with pytest.raises(ValidationError):
        SecurityService.validate_url("magnet:?dn=NoXT")

    # Local SSRF blocked for HTTP/HTTPS with SSRFSecurityError
    with pytest.raises(SSRFSecurityError):
        SecurityService.validate_url("http://127.0.0.1/video.mp4")


def test_input_detector_routing():
    mag = "magnet:?xt=urn:btih:0123456789abcdef0123456789abcdef01234567"
    assert InputDetector.detect(mag) == "torrent_magnet"
    assert InputDetector.get_provider(mag) == "torrent"
    assert InputDetector.get_input_type(mag) == "magnet"

    http_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert InputDetector.detect(http_url) == "ytdlp"
    assert InputDetector.get_provider(http_url) == "ytdlp"
    assert InputDetector.get_input_type(http_url) == "url"


# ---------------------------------------------------------------------------
# 4. Duplicate Detection Tests
# ---------------------------------------------------------------------------

def test_duplicate_magnet_detection():
    ih = "1234567890abcdef1234567890abcdef12345678"
    tor_id = str(uuid.uuid4())
    TorrentRepository.save_torrent({
        "id": tor_id,
        "info_hash": ih,
        "name": "Existing Torrent",
        "status": "DOWNLOADING",
    })

    # Same hash, different dn or tracker parameters
    mag1 = f"magnet:?xt=urn:btih:{ih}&dn=Name+A"
    mag2 = f"magnet:?xt=urn:btih:{ih}&dn=Name+B&tr=udp%3A%2F%2Ftracker.org"

    is_dup1, reason1, _ = DuplicateDetector.check_duplicate(mag1)
    is_dup2, reason2, _ = DuplicateDetector.check_duplicate(mag2)

    assert is_dup1 is True
    assert is_dup2 is True
    assert "already exists or is already queued" in reason1

    # Different info hash
    mag3 = "magnet:?xt=urn:btih:ffffffffffffffffffffffffffffffffffffffff"
    is_dup3, _, _ = DuplicateDetector.check_duplicate(mag3)
    assert is_dup3 is False


# ---------------------------------------------------------------------------
# 5. Low-Level Error Mapping
# ---------------------------------------------------------------------------

def test_map_torrent_error():
    assert map_torrent_error("invalid magnet URI provided") == "Invalid magnet"
    assert map_torrent_error("metadata timeout after 300s") == "Metadata timeout"
    assert map_torrent_error("tracker connection refused") == "Tracker unavailable"
    assert map_torrent_error("no peers found in swarm") == "No peers"
    assert map_torrent_error("libtorrent session failure") == "Engine unavailable"
    assert map_torrent_error("enospc: no space left on device") == "Disk/storage error"
    assert map_torrent_error("eacces: permission denied") == "Permission error"
    assert map_torrent_error("network unreachable") == "Network error"
    assert map_torrent_error("completely unexpected failure") == "Torrent engine error"


# ---------------------------------------------------------------------------
# 6. API Endpoints Integration Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_system_info_torrent_status():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/system")
        assert res.status_code == 200
        data = res.json()
        assert data["torrent_enabled"] is True
        assert data["torrent_engine_status"] in ("healthy", "starting", "unavailable")


@pytest.mark.asyncio
async def test_download_endpoint_magnet_submission():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        unique_hash = (uuid.uuid4().hex + uuid.uuid4().hex)[:40]
        magnet = f"magnet:?xt=urn:btih:{unique_hash}&dn=Unique+Download+Test"

        # 1. First submission succeeds
        res = await ac.post("/api/download", json={"url": magnet})
        assert res.status_code == 200
        data = res.json()
        job_id = data["job_id"]
        assert job_id is not None

        # Verify job properties in DB
        job = JobRepository.get_job(job_id)
        assert job is not None
        assert job.provider == "torrent"
        assert job.input_type == "magnet"
        assert job.info_hash == unique_hash

        # 2. Duplicate submission returns 409 Conflict
        res_dup = await ac.post("/api/download", json={"url": magnet})
        assert res_dup.status_code == 409
        dup_data = res_dup.json()
        assert "already exists or is already queued" in dup_data["detail"]
        assert dup_data["existing_job_id"] == job_id

        # 3. Duplicate submission with override_duplicate=True succeeds
        res_override = await ac.post("/api/download", json={"url": magnet, "override_duplicate": True})
        assert res_override.status_code == 200
        assert res_override.json()["job_id"] is not None


@pytest.mark.asyncio
async def test_automation_v1_jobs_magnet_submission():
    raw_key, key_rec = ApiKeyRepository.create_key("v1_magnet_test_key")
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            unique_hash = (uuid.uuid4().hex + uuid.uuid4().hex)[:40]
            magnet = f"magnet:?xt=urn:btih:{unique_hash}&dn=V1+Automation+Test"

            res = await ac.post(
                "/api/v1/jobs",
                json={"url": magnet},
                headers={"X-API-Key": raw_key},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["job_id"] is not None

            job = JobRepository.get_job(data["job_id"])
            assert job is not None
            assert job.provider == "torrent"
            assert job.input_type == "magnet"
            assert job.info_hash == unique_hash
    finally:
        ApiKeyRepository.delete_key(key_rec["id"])
