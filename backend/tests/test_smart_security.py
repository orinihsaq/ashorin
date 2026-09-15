import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_watcher_ssrf_protection():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Private LAN IP in watcher URL
        res = await ac.post("/api/watchers", json={
            "name": "Malicious LAN Watcher",
            "source_url": "http://192.168.1.1/playlist",
        })
        assert res.status_code == 400
        assert "restricted" in res.json()["detail"].lower()

        # 2. Cloud metadata IP in watcher URL
        res = await ac.post("/api/watchers", json={
            "name": "Cloud Metadata Watcher",
            "source_url": "http://169.254.169.254/latest/meta-data/",
        })
        assert res.status_code == 400
        assert "restricted" in res.json()["detail"].lower()

        # 3. Localhost loopback in watcher URL
        res = await ac.post("/api/watchers", json={
            "name": "Localhost Watcher",
            "source_url": "http://127.0.0.1:8080/secret",
        })
        assert res.status_code == 400
        assert "restricted" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_v1_automation_api_security():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Without key -> 401
        res = await ac.get("/api/v1/watchers")
        assert res.status_code == 401

        res = await ac.get("/api/v1/recipes")
        assert res.status_code == 401

        # Invalid key -> 401
        res = await ac.get("/api/v1/watchers", headers={"X-API-Key": "invalid_key"})
        assert res.status_code == 401
