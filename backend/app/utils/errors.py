import re
from typing import Optional

class AppException(Exception):
    """Base application exception."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ValidationError(AppException):
    def __init__(self, message: str = "Invalid input"):
        super().__init__(message, status_code=422)


class SSRFSecurityError(AppException):
    def __init__(self, message: str = "Access to local or private network addresses is restricted."):
        super().__init__(message, status_code=403)


class MediaUnavailableError(AppException):
    def __init__(self, message: str = "This media is currently unavailable or private."):
        super().__init__(message, status_code=404)


class DRMProtectedError(AppException):
    def __init__(self, message: str = "This media appears to use DRM and cannot be downloaded by this application."):
        super().__init__(message, status_code=403)


class UnsupportedWebsiteError(AppException):
    def __init__(self, message: str = "This website is not currently supported by yt-dlp."):
        super().__init__(message, status_code=400)


class JobNotFoundError(AppException):
    def __init__(self, message: str = "Download job not found"):
        super().__init__(message, status_code=404)


class JobCancelledError(AppException):
    def __init__(self, message: str = "Job was cancelled by user"):
        super().__init__(message, status_code=499)


class FileTooLargeError(AppException):
    def __init__(self, message: str = "Media file exceeds maximum allowed download size."):
        super().__init__(message, status_code=413)


def map_ytdlp_error(raw_error: Optional[str]) -> str:
    """
    Map raw yt-dlp error outputs / exceptions to clean, user-friendly error messages.
    Never exposes raw Python tracebacks or internal system details.
    """
    if not raw_error:
        return "Something went wrong while processing the download."

    err = raw_error.lower()

    # DRM protection
    if "drm" in err or "protected content" in err or "widevine" in err or "fairplay" in err:
        return "This media appears to use DRM and cannot be downloaded by this application."

    # Unsupported extractor or website
    if "unsupported url" in err or "no suitable extractor" in err or "not currently supported" in err:
        return "This website is not currently supported by yt-dlp."

    # Format unavailable
    if "requested format is not available" in err or "no video formats found" in err or "format unavailable" in err:
        return "The selected quality is no longer available."

    # Authentication / Login required
    if "login" in err or "sign in" in err or "private video" in err or "members-only" in err or "account required" in err:
        return "This content requires authentication or is private, and cannot be accessed."

    # Geo-restriction
    if "geo-restricted" in err or "not available in your country" in err or "geoblocked" in err:
        return "This media is geo-restricted and not available in the server's region."

    # Video deleted / unavailable
    if "video unavailable" in err or "has been removed" in err or "deleted" in err or "404: not found" in err:
        return "This media is currently unavailable or has been removed."

    # Network failures
    if "timed out" in err or "connection refused" in err or "unable to download webpage" in err or "network is unreachable" in err or "temporary failure in name resolution" in err:
        return "The remote website could not be reached. Please try again."

    # File size limit exceeded
    if "file is larger than max-filesize" in err or "exceeds maximum allowed" in err:
        return "Media file exceeds maximum allowed download size."

    # Generic friendly fallback
    return "Something went wrong while processing the download."
