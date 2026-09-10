from app.utils.errors import map_ytdlp_error


def test_map_drm_error():
    err = "ERROR: [generic] This video is DRM protected."
    mapped = map_ytdlp_error(err)
    assert "DRM" in mapped


def test_map_unsupported_website_error():
    err = "ERROR: Unsupported URL: https://unknown-site.xyz/abc"
    mapped = map_ytdlp_error(err)
    assert "not currently supported" in mapped


def test_map_format_unavailable_error():
    err = "ERROR: requested format is not available"
    mapped = map_ytdlp_error(err)
    assert "no longer available" in mapped


def test_map_login_required_error():
    err = "ERROR: Sign in to confirm your age. This video may be inappropriate for some users."
    mapped = map_ytdlp_error(err)
    assert "authentication" in mapped


def test_map_network_error():
    err = "ERROR: <urlopen error timed out>"
    mapped = map_ytdlp_error(err)
    assert "could not be reached" in mapped


def test_map_unknown_error():
    err = "Some unknown weird python stacktrace"
    mapped = map_ytdlp_error(err)
    assert mapped == "Something went wrong while processing the download."
