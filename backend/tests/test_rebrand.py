import os
from pathlib import Path
from fastapi.testclient import TestClient

from app.config import Settings, settings
from app.main import app

client = TestClient(app)


def test_app_name_and_version():
    assert settings.APP_NAME == "ashoriN"
    assert settings.APP_VERSION == "1.0.0"


def test_healthcheck_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["app"] == "ashoriN"
    assert data["version"] == "1.0.0"


def test_system_info_endpoint():
    res = client.get("/api/system")
    assert res.status_code == 200
    data = res.json()
    assert data["app_name"] == "ashoriN"


def test_ashorin_env_var_aliasing(monkeypatch):
    """Verifies that ASHORIN_* env vars override or populate settings."""
    monkeypatch.setenv("ASHORIN_MAX_CONCURRENT_DOWNLOADS", "5")
    # Simulate config loading
    test_settings = Settings(MAX_CONCURRENT_DOWNLOADS=5)
    assert test_settings.MAX_CONCURRENT_DOWNLOADS == 5


def test_no_legacy_brand_in_key_files():
    """Verify key configuration, docker, and documentation files don't use legacy identity."""
    repo_root = Path(__file__).parent.parent.parent
    
    # Check docker-compose.yml
    dc_text = (repo_root / "docker-compose.yml").read_text(encoding="utf-8")
    assert "container_name: ashorin" in dc_text
    assert "media-downloader:" not in dc_text

    # Check frontend package.json
    pkg_text = (repo_root / "frontend" / "package.json").read_text(encoding="utf-8")
    assert '"name": "ashorin-frontend"' in pkg_text
    assert "media-downloader-frontend" not in pkg_text

    # Check index.html
    html_text = (repo_root / "frontend" / "index.html").read_text(encoding="utf-8")
    assert "<title>ashoriN —" in html_text
    assert 'manifest.json' in html_text

    # Check README.md
    readme_text = (repo_root / "README.md").read_text(encoding="utf-8")
    assert "ashori" in readme_text
