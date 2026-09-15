import asyncio
import json
import socket
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
import pytest
from httpx import ASGITransport, AsyncClient, Response, Request

from app.db.database import get_db
from app.main import app
from app.services.discovery.tmdb_client import (
    TMDBClient,
    sanitize_url,
    TMDB_CONNECTION_TIMEOUT,
    TMDB_READ_TIMEOUT,
    TMDB_DNS_FAILURE,
    TMDB_TLS_ERROR,
    TMDB_CONNECT_REFUSED,
    TMDB_UNAUTHORIZED,
    TMDB_FORBIDDEN,
    TMDB_RATE_LIMIT,
    TMDB_UPSTREAM_ERROR,
)
from app.services.discovery.discovery_service import DiscoveryService
from app.services.settings_service import settings_service
from app.utils.errors import TMDBError, MediaDiscoveryDisabledError, TMDBNotConfiguredError


@pytest.fixture(autouse=True)
def reset_discovery_settings():
    """Ensures discovery settings and cache are clean before and after each test."""
    settings_service.update_settings(
        media_discovery_enabled=False,
        tmdb_enabled=False,
        tmdb_api_key="",
    )
    with get_db() as conn:
        conn.execute("DELETE FROM discovery_cache")
        conn.execute("DELETE FROM discovered_movies")
        conn.execute("DELETE FROM discovered_series")
        conn.commit()
    yield
    settings_service.update_settings(
        media_discovery_enabled=False,
        tmdb_enabled=False,
        tmdb_api_key="",
    )
    with get_db() as conn:
        conn.execute("DELETE FROM discovery_cache")
        conn.execute("DELETE FROM discovered_movies")
        conn.execute("DELETE FROM discovered_series")
        conn.commit()


# ── 1. Credential Sanitization ──────────────────────────────────────────

def test_sanitize_url_redacts_api_key_and_bearer():
    url1 = "https://api.themoviedb.org/3/authentication?api_key=my_super_secret_key_12345&language=en"
    sanitized1 = sanitize_url(url1)
    assert "my_super_secret_key_12345" not in sanitized1
    assert "api_key=••••••••" in sanitized1
    assert "language=en" in sanitized1

    url2 = "https://api.themoviedb.org/3/movie/550"
    sanitized2 = sanitize_url(url2)
    assert sanitized2 == url2


# ── 2. Connection Pooling & Re-use ──────────────────────────────────────

@pytest.mark.asyncio
async def test_tmdb_client_uses_connection_pool():
    """Ensures TMDBClient creates and reuses an httpx.AsyncClient with connection limits."""
    client = TMDBClient(api_key="test_key_123")
    try:
        raw_client = await client._get_client()
        assert isinstance(raw_client, httpx.AsyncClient)
        # Re-access returns same client instance (pooling)
        assert await client._get_client() is raw_client
        assert raw_client.timeout.connect == 5.0   # _PROBE_CONNECT_TIMEOUT
        assert raw_client.timeout.read == 30.0
    finally:
        await client.close()


# ── 3. Test Connection Success ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_tmdb_client_test_connection_success():
    """Tests successful authentication against TMDB /authentication."""
    client = TMDBClient(api_key="test_key_123")
    try:
        raw_client = await client._get_client()
        mock_resp = Response(
            200,
            headers={"content-type": "application/json"},
            json={"success": True, "status_code": 1, "status_message": "Success."},
            request=Request("GET", "https://api.themoviedb.org/3/authentication"),
        )
        with patch.object(raw_client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            result = await client.test_connection()
            assert result["success"] is True
            assert result["status_code"] == 200
            assert result["dns_ok"] is True
            assert "Successfully connected" in result["message"]
            assert result["latency_ms"] is not None
    finally:
        await client.close()


# ── 4. Error Classifications (401, 403, 429, 503, ConnectTimeout, etc.) ─

@pytest.mark.asyncio
async def test_tmdb_client_test_connection_401():
    """Tests invalid API key classification (HTTP 401)."""
    client = TMDBClient(api_key="invalid_key")
    try:
        raw_client = await client._get_client()
        mock_resp = Response(
            401,
            json={"status_code": 7, "status_message": "Invalid API key."},
            request=Request("GET", "https://api.themoviedb.org/3/authentication"),
        )
        with patch.object(raw_client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            result = await client.test_connection()
            assert result["success"] is False
            assert result["status_code"] == 401
            assert result["error_code"] == "HTTP_401"
            assert "rejected the configured credentials" in result["message"]
            assert result["retryable"] is False
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_tmdb_client_test_connection_403():
    """Tests access denied classification (HTTP 403)."""
    client = TMDBClient(api_key="forbidden_key")
    try:
        raw_client = await client._get_client()
        mock_resp = Response(
            403,
            json={"status_code": 10, "status_message": "Suspended API key."},
            request=Request("GET", "https://api.themoviedb.org/3/authentication"),
        )
        with patch.object(raw_client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            result = await client.test_connection()
            assert result["success"] is False
            assert result["status_code"] == 403
            assert result["error_code"] == "HTTP_403"
            assert "forbidden" in result["message"].lower()
            assert result["retryable"] is False
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_tmdb_client_test_connection_429():
    """Tests rate limit classification (HTTP 429)."""
    client = TMDBClient(api_key="valid_key")
    try:
        raw_client = await client._get_client()
        mock_resp = Response(
            429,
            headers={"Retry-After": "5"},
            json={"status_code": 25, "status_message": "Too many requests."},
            request=Request("GET", "https://api.themoviedb.org/3/authentication"),
        )
        with patch.object(raw_client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            result = await client.test_connection()
            assert result["success"] is False
            assert result["status_code"] == 429
            assert result["error_code"] == "HTTP_429"
            assert "rate-limited" in result["message"].lower()
            assert result["retryable"] is False
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_tmdb_client_test_connection_503():
    """Tests TMDB server error (HTTP 503)."""
    client = TMDBClient(api_key="valid_key")
    try:
        raw_client = await client._get_client()
        mock_resp = Response(
            503,
            text="Service Unavailable",
            request=Request("GET", "https://api.themoviedb.org/3/authentication"),
        )
        with patch.object(raw_client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            result = await client.test_connection()
            assert result["success"] is False
            assert result["status_code"] == 503
            assert result["error_code"] == "HTTP_5XX"
            assert result["retryable"] is True
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_tmdb_client_connect_timeout_classification():
    """Tests connect timeout classification and error handling."""
    client = TMDBClient(api_key="valid_key")
    try:
        raw_client = await client._get_client(ipv4_only=False)
        raw_v4 = await client._get_client(ipv4_only=True)
        # Both dual-stack and fallback fail with ConnectTimeout
        with patch.object(raw_client, "get", side_effect=httpx.ConnectTimeout("Connection timed out")), \
             patch.object(raw_v4, "get", side_effect=httpx.ConnectTimeout("Connection timed out")):
            result = await client.test_connection()
            assert result["success"] is False
            assert result["error_code"] == "CONNECTION_TIMEOUT"
            assert "timed out while establishing connection" in result["message"]
            assert result["retryable"] is True
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_tmdb_client_dns_failure_classification():
    """Tests DNS resolution failure classification."""
    client = TMDBClient(api_key="valid_key")
    try:
        raw_client = await client._get_client(ipv4_only=False)
        with patch.object(client, "check_dns", new_callable=AsyncMock) as mock_dns, \
             patch.object(raw_client, "get", side_effect=httpx.ConnectError("getaddrinfo failed")):
            mock_dns.return_value = (False, "DNS resolution failed: [Errno -2] Name or service not known")
            result = await client.test_connection()
            assert result["success"] is False
            assert result["dns_ok"] is False
            assert result["error_code"] == "DNS_FAILURE"
            assert "Cannot resolve TMDB hostname" in result["message"]
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_tmdb_client_tls_error_classification():
    """Tests TLS / certificate verification error classification."""
    client = TMDBClient(api_key="valid_key")
    try:
        raw_client = await client._get_client()
        with patch.object(raw_client, "get", side_effect=httpx.ConnectError("[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed")):
            result = await client.test_connection()
            assert result["success"] is False
            assert result["error_code"] == "TLS_ERROR"
            assert "TLS certificate verification failed" in result["message"]
            assert result["retryable"] is False
    finally:
        await client.close()


# ── 5. Dual-Stack IPv4 Fallback ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_tmdb_client_ipv4_fallback_on_connect_timeout():
    """
    Verifies that TMDBClient falls back to IPv4 transport when dual-stack times out.

    Temporarily clears _force_ipv4_only so the dual-stack transport is attempted
    first (as happens on systems with a broken — not absent — IPv6 WAN route).
    The ConnectTimeout on the dual-stack client then triggers the IPv4 fallback.
    """
    client = TMDBClient(api_key="valid_key")
    # Override the auto-detected flag so the dual-stack path is exercised
    client._force_ipv4_only = False
    try:
        raw_client = await client._get_client(ipv4_only=False)   # dual-stack client
        raw_v4 = await client._get_client(ipv4_only=True)        # ipv4-only client

        # The two clients must be distinct objects for the mock to work properly
        assert raw_client is not raw_v4, (
            "dual-stack and ipv4-only clients must be separate httpx.AsyncClient instances"
        )

        mock_resp = Response(
            200,
            headers={"content-type": "application/json"},
            json={"success": True, "status_code": 1, "status_message": "Success."},
            request=Request("GET", "https://api.themoviedb.org/3/authentication"),
        )
        with patch.object(raw_client, "get", side_effect=httpx.ConnectTimeout("IPv6 dropped")), \
             patch.object(raw_v4, "get", return_value=mock_resp):
            result = await client.test_connection()
            assert result["success"] is True
            assert result["status_code"] == 200
            assert "IPv4 fallback" in result["message"]
    finally:
        await client.close()


# ── 6. Retry with Backoff on 502/503/504 ────────────────────────────────

@pytest.mark.asyncio
async def test_tmdb_retries_with_backoff_on_transient_502():
    """Verifies bounded retries on 502/503/504 upstream errors."""
    client = TMDBClient(api_key="valid_key")
    try:
        call_count = 0
        success_resp = Response(
            200,
            headers={"content-type": "application/json"},
            json={"id": 550, "title": "Fight Club"},
            request=Request("GET", "https://api.themoviedb.org/3/movie/550"),
        )
        bad_resp = Response(
            502,
            text="Bad Gateway",
            request=Request("GET", "https://api.themoviedb.org/3/movie/550"),
        )

        raw_client = await client._get_client(ipv4_only=False)

        async def fake_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return bad_resp
            return success_resp

        with patch.object(raw_client, "get", side_effect=fake_get):
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                data = await client.get_movie_details(550)
                assert data["title"] == "Fight Club"
                assert call_count == 2
                assert mock_sleep.called
    finally:
        await client.close()


# ── 7. Endpoint Integration Tests (POST /api/discovery/tmdb/test) ───────

@pytest.mark.asyncio
async def test_endpoint_tmdb_test_not_configured():
    """POST /api/discovery/tmdb/test returns TMDB_NOT_CONFIGURED when no key is set or passed."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post("/api/discovery/tmdb/test", json={})
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is False
        assert data["error_code"] == "TMDB_NOT_CONFIGURED"
        assert "not configured" in data["message"].lower()


@pytest.mark.asyncio
async def test_endpoint_tmdb_test_with_configured_key():
    """POST /api/discovery/tmdb/test uses configured key when none in body."""
    settings_service.update_settings(
        media_discovery_enabled=True,
        tmdb_enabled=True,
        tmdb_api_key="conf_secret_key_999",
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        with patch.object(TMDBClient, "test_connection", new_callable=AsyncMock) as mock_test:
            mock_test.return_value = {
                "success": True,
                "provider": "tmdb",
                "latency_ms": 120,
                "status_code": 200,
                "error_code": None,
                "message": "Successfully authenticated with TMDB.",
                "retryable": False,
                "dns_ok": True,
            }
            res = await ac.post("/api/discovery/tmdb/test", json={})
            assert res.status_code == 200
            data = res.json()
            assert data["success"] is True
            assert data["latency_ms"] == 120
            # Ensure no credentials leaked in response
            assert "conf_secret_key_999" not in json.dumps(data)


@pytest.mark.asyncio
async def test_endpoint_tmdb_test_with_transient_key():
    """POST /api/discovery/tmdb/test tests a transient key without needing to save first."""
    transient_key = "transient_user_input_key_456"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        with patch.object(TMDBClient, "test_connection", new_callable=AsyncMock) as mock_test:
            mock_test.return_value = {
                "success": True,
                "provider": "tmdb",
                "latency_ms": 88,
                "status_code": 200,
                "error_code": None,
                "message": "Successfully authenticated with TMDB.",
                "retryable": False,
                "dns_ok": True,
            }
            res = await ac.post("/api/discovery/tmdb/test", json={"api_key": transient_key})
            assert res.status_code == 200
            data = res.json()
            assert data["success"] is True
            # Check transient key was not persisted to settings
            assert settings_service.tmdb_api_key != transient_key
            # Check key not leaked in response
            assert transient_key not in json.dumps(data)


# ── 8. DiscoveryService Persistent Client Caching & Lifecycle ────────────

@pytest.mark.asyncio
async def test_discovery_service_persistent_client_caching():
    """Verifies that DiscoveryService caches and invalidates TMDBClient when key changes."""
    settings_service.update_settings(
        media_discovery_enabled=True,
        tmdb_enabled=True,
        tmdb_api_key="key_1",
    )
    c1 = DiscoveryService._ensure_active()
    assert DiscoveryService._ensure_active() is c1

    # When key changes, old client is invalidated
    settings_service.update_settings(tmdb_api_key="key_2")
    c2 = DiscoveryService._ensure_active()
    assert c2 is not c1

    await DiscoveryService.shutdown()
    assert DiscoveryService._tmdb_client is None
