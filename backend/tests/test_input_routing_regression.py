"""
Regression test suite for Input Routing Architecture:
Ensures magnet links bypass yt-dlp and HTTP SSRF validators entirely,
and validates Section 20, 21, 22, 23 requirements.
"""

from unittest.mock import AsyncMock, patch
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.input_router import detect_input_type, get_provider_for_input, InputRouter, InputType
from app.services.security import SecurityService
from app.services.torrent.magnet import MagnetParser, MagnetValidator
from app.services.yt_dlp import YtDlpService
from app.utils.errors import InvalidMagnetError, ValidationError


# ---------------------------------------------------------------------------
# Section 20: Mandatory Regression Test — Magnet must NEVER call YtDlpService
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_magnet_never_calls_ytdlp_analyze():
    """
    MANDATORY REGRESSION TEST:
    Verifies that when a valid magnet URI is analyzed:
      - input_type is detected as MAGNET_URI
      - provider is routed to TORRENT
      - YtDlpService.analyze_url() is NEVER called under any circumstances
    """
    valid_hash = "0123456789abcdef0123456789abcdef01234567"
    magnet_uri = f"magnet:?xt=urn:btih:{valid_hash}&dn=Ubuntu+Desktop"

    # 1. Canonical detector verification
    itype = detect_input_type(magnet_uri)
    assert itype == InputType.MAGNET_URI

    provider = get_provider_for_input(magnet_uri)
    assert provider == "torrent"

    # 2. Mock YtDlpService.analyze_url and verify it is NEVER invoked
    with patch.object(YtDlpService, "analyze_url", new_callable=AsyncMock) as mock_ytdlp_analyze:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.post("/api/analyze", json={"url": magnet_uri})

        assert res.status_code == 200
        data = res.json()
        assert data["type"] == "torrent"
        assert data["input_type"] == "magnet"
        assert data["info_hash"] == valid_hash
        assert mock_ytdlp_analyze.call_count == 0


# ---------------------------------------------------------------------------
# Section 21: Test HTTP/HTTPS Regression
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_https_regression_routing_and_ssrf():
    """
    Verifies normal HTTPS media URLs:
      - detected as HTTPS_URL
      - provider = ytdlp
      - uses existing SSRF protection
    """
    https_url = "https://www.youtube.com/watch?v=aqz-KE-bpKQ"
    assert detect_input_type(https_url) == InputType.HTTPS_URL
    assert get_provider_for_input(https_url) == "ytdlp"

    from app.utils.errors import SSRFSecurityError

    # SSRF protection must still block private IP ranges for HTTP/HTTPS
    with pytest.raises(SSRFSecurityError):
        SecurityService.validate_http_url("http://127.0.0.1/malicious.mp4")

    with pytest.raises(SSRFSecurityError):
        SecurityService.validate_http_url("http://localhost:8080/secret")


# ---------------------------------------------------------------------------
# Section 22: Test Invalid Inputs
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("invalid_input", [
    "hello",
    "ftp://example.com/file.iso",
    "file:///etc/passwd",
    "magnet:",
    "magnet:?dn=test",
    "magnet:?xt=",
])
@pytest.mark.asyncio
async def test_invalid_inputs_rejected_without_ytdlp(invalid_input):
    """
    Verifies invalid inputs produce a clean 422 validation error
    and NEVER enter yt-dlp analysis.
    """
    with patch.object(YtDlpService, "analyze_url", new_callable=AsyncMock) as mock_ytdlp_analyze:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.post("/api/analyze", json={"url": invalid_input})

        assert res.status_code == 422
        body = res.json()
        assert "error" in body or "detail" in body
        # YtDlpService must NEVER have been called
        assert mock_ytdlp_analyze.call_count == 0


# ---------------------------------------------------------------------------
# Section 23: Test Multiple Magnet Parameters survive without corruption
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_multiple_magnet_parameters_survive():
    """
    Verifies that:
      xt, dn, tr, tr parameters survive:
      Frontend -> JSON -> FastAPI -> TorrentProvider -> torrent engine
      without:
        - truncation
        - double encoding
        - plus-to-space conversion
        - ampersand splitting
    """
    hash_hex = "abcdef0123456789abcdef0123456789abcdef01"
    tracker1 = "udp://tracker.openbittorrent.com:80/announce"
    tracker2 = "http://tracker.opentrackr.org:1337/announce"
    encoded_tr1 = "udp%3A%2F%2Ftracker.openbittorrent.com%3A80%2Fannounce"
    encoded_tr2 = "http%3A%2F%2Ftracker.opentrackr.org%3A1337%2Fannounce"

    complex_magnet = (
        f"magnet:?xt=urn:btih:{hash_hex}"
        f"&dn=Ubuntu+24.04+LTS+Desktop"
        f"&tr={encoded_tr1}"
        f"&tr={encoded_tr2}"
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post("/api/analyze", json={"url": complex_magnet})

    assert res.status_code == 200
    data = res.json()

    assert data["type"] == "torrent"
    assert data["info_hash"] == hash_hex
    # Preserves '+' in dn without conversion to space
    assert "Ubuntu+24.04+LTS+Desktop" in data["magnet_uri"]
    # All trackers preserved without truncation
    assert len(data["trackers"]) == 2
    assert tracker1 in data["trackers"]
    assert tracker2 in data["trackers"]
