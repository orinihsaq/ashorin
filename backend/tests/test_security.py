import pytest
from app.services.security import SecurityService
from app.utils.errors import SSRFSecurityError, ValidationError


def test_valid_https_url():
    url = "https://example.com/video/123"
    result = SecurityService.validate_url(url)
    assert result == url


def test_rejects_empty_or_none():
    with pytest.raises(ValidationError):
        SecurityService.validate_url("")
    with pytest.raises(ValidationError):
        SecurityService.validate_url(None)


def test_rejects_dangerous_schemes():
    dangerous = [
        "file:///etc/passwd",
        "ftp://ftp.example.com/file.mp4",
        "data:text/plain;base64,SGVsbG8=",
        "javascript:alert(1)",
        "gopher://127.0.0.1:70",
    ]
    for url in dangerous:
        with pytest.raises(ValidationError):
            SecurityService.validate_url(url)


def test_rejects_localhost_and_loopback():
    loopbacks = [
        "http://localhost:8080/media",
        "http://127.0.0.1:8000/test",
        "http://127.0.0.2:80",
        "http://127.255.255.254:3000",
    ]
    for url in loopbacks:
        with pytest.raises(SSRFSecurityError):
            SecurityService.validate_url(url)


def test_rejects_private_networks():
    privates = [
        "http://10.0.0.1/video.mp4",
        "http://10.254.1.1:8080",
        "http://172.16.0.5/stream",
        "http://172.31.255.255:9000",
        "http://192.168.1.1/admin",
        "http://192.168.100.20",
    ]
    for url in privates:
        with pytest.raises(SSRFSecurityError):
            SecurityService.validate_url(url)


def test_rejects_cloud_metadata():
    metadata_endpoints = [
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://instance-data/latest/meta-data/",
    ]
    for url in metadata_endpoints:
        with pytest.raises(SSRFSecurityError):
            SecurityService.validate_url(url)


def test_rejects_control_characters():
    with pytest.raises(ValidationError):
        SecurityService.validate_url("https://example.com/test\r\nCRLF")
