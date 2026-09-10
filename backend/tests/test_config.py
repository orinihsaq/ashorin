import pytest
from app.config import Settings, parse_bytes


def test_parse_bytes():
    assert parse_bytes("1024") == 1024
    assert parse_bytes("1K") == 1024
    assert parse_bytes("1KB") == 1024
    assert parse_bytes("1M") == 1024**2
    assert parse_bytes("500MB") == 500 * 1024**2
    assert parse_bytes("10G") == 10 * 1024**3
    assert parse_bytes("2GB") == 2 * 1024**3


def test_parse_bytes_invalid():
    with pytest.raises(ValueError):
        parse_bytes("invalid_size")
    with pytest.raises(ValueError):
        parse_bytes("10XYZ")


def test_settings_defaults():
    s = Settings()
    assert s.APP_NAME == "ashoriN"
    assert s.MAX_CONCURRENT_DOWNLOADS >= 1
    assert s.DOWNLOAD_RETENTION >= 0
    assert s.TEMP_RETENTION >= 0
    assert s.max_download_size_bytes > 0
