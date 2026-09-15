import pytest
from typing import Any

from app.models.schemas import TorrentTelemetry
from app.services.torrent.engine import (
    HAS_LIBTORRENT,
    TorrentStatus,
    map_torrent_state,
)


class MockStatusObject:
    def __init__(
        self,
        state: Any = "downloading",
        paused: bool = False,
        is_seeding: bool = False,
        is_finished: bool = False,
        has_metadata: bool = True,
    ):
        self.state = state
        self.paused = paused
        self.is_seeding = is_seeding
        self.is_finished = is_finished
        self.has_metadata = has_metadata


def test_map_torrent_state_string_inputs():
    """Verify all string variations map to normalized application states."""
    assert map_torrent_state("checking") == "checking"
    assert map_torrent_state("checking_files") == "checking"
    assert map_torrent_state("allocating") == "checking"
    assert map_torrent_state("queued_for_checking") == "checking"

    assert map_torrent_state("downloading_metadata") == "metadata"
    assert map_torrent_state("metadata") == "metadata"

    assert map_torrent_state("downloading") == "downloading"
    assert map_torrent_state("finished") == "finished"
    assert map_torrent_state("seeding") == "seeding"

    assert map_torrent_state("checking_resume_data") == "checking_resume"
    assert map_torrent_state("checking_resume") == "checking_resume"

    assert map_torrent_state("paused") == "paused"

    # Invalid / unrecognized / edge cases
    assert map_torrent_state(None) == "unknown"
    assert map_torrent_state("") == "unknown"
    assert map_torrent_state("some_unrecognized_state") == "unknown"
    assert map_torrent_state(12345) == "unknown"


def test_map_torrent_state_object_flags():
    """Verify boolean status flags take proper precedence."""
    # Paused flag overrides download state
    assert map_torrent_state(MockStatusObject(state="downloading", paused=True)) == "paused"

    # Missing metadata flag yields metadata state
    assert map_torrent_state(MockStatusObject(state="downloading", has_metadata=False)) == "metadata"

    # Seeding flag yields seeding state
    assert map_torrent_state(MockStatusObject(state="downloading", is_seeding=True)) == "seeding"

    # Finished flag yields finished state
    assert map_torrent_state(MockStatusObject(state="downloading", is_finished=True)) == "finished"

    # Checking state
    assert map_torrent_state(MockStatusObject(state="checking_files")) == "checking"
    assert map_torrent_state(MockStatusObject(state="allocating")) == "checking"

    # Checking resume state
    assert map_torrent_state(MockStatusObject(state="checking_resume_data")) == "checking_resume"


def test_map_torrent_state_dict_inputs():
    """Verify dict-like status containers map correctly."""
    assert map_torrent_state({"state": "downloading", "is_paused": True}) == "paused"
    assert map_torrent_state({"state": "downloading", "has_metadata": False}) == "metadata"
    assert map_torrent_state({"state": "downloading", "is_seeding": True}) == "seeding"
    assert map_torrent_state({"state": "downloading", "is_finished": True}) == "finished"
    assert map_torrent_state({"state": "checking_files"}) == "checking"
    assert map_torrent_state({"state": "downloading"}) == "downloading"


def test_map_torrent_state_with_mocked_libtorrent_enums():
    """Verify libtorrent states enum mapping when libtorrent is mocked or present."""
    # Create mock libtorrent states enum
    class MockLtEnum:
        def __init__(self, name: str):
            self.name = name

        def __str__(self):
            return f"libtorrent.states.{self.name}"

    assert map_torrent_state(MockLtEnum("checking_files")) == "checking"
    assert map_torrent_state(MockLtEnum("downloading_metadata")) == "metadata"
    assert map_torrent_state(MockLtEnum("downloading")) == "downloading"
    assert map_torrent_state(MockLtEnum("finished")) == "finished"
    assert map_torrent_state(MockLtEnum("seeding")) == "seeding"
    assert map_torrent_state(MockLtEnum("checking_resume_data")) == "checking_resume"
    assert map_torrent_state(MockLtEnum("allocating")) == "checking"


def test_no_state_t_in_codebase():
    """Ensure no code attempts to use lt.torrent_status.state_t."""
    from pathlib import Path
    backend_dir = Path(__file__).resolve().parent.parent / "app"

    offending_files = []
    for py_file in backend_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        if "state_t" in content:
            # Only allow save_resume_flags_t if safely wrapped, but never torrent_status.state_t
            if "torrent_status.state_t" in content or ".state_t" in content:
                offending_files.append(str(py_file))

    assert not offending_files, f"Found references to state_t in: {offending_files}"


def test_torrent_status_to_dict_and_normalization():
    """Verify TorrentStatus dataclass exposes normalized states and clean dict."""
    status = TorrentStatus(
        info_hash="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e",
        name="Ubuntu 24.04 Desktop ISO",
        state=map_torrent_state("checking_files"),
        progress=0.45,
        download_rate=1048576,
        upload_rate=524288,
        total_downloaded=500000000,
        total_uploaded=250000000,
        total_size=1000000000,
        num_peers=25,
        num_seeds=50,
        num_leeches=10,
        ratio=0.5,
        is_seeding=False,
        is_finished=False,
        is_paused=False,
        has_metadata=True,
    )

    assert status.state == "checking"
    d = status.to_dict()
    assert d["state"] == "checking"
    assert isinstance(d["state"], str)
    assert d["info_hash"] == "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e"
    assert d["progress"] == 0.45


def test_torrent_telemetry_state_field():
    """Verify TorrentTelemetry schema includes normalized state field."""
    telemetry = TorrentTelemetry(
        info_hash="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e",
        name="Test",
        state="metadata",
        total_size=1000,
        total_size_formatted="1.0 KB",
        downloaded_bytes=0,
        uploaded_bytes=0,
        download_speed="0 B/s",
        upload_speed="0 B/s",
        ratio=0.0,
        peers=0,
        seeds=0,
        leeches=0,
    )
    assert telemetry.state == "metadata"
    data = telemetry.model_dump()
    assert data["state"] == "metadata"
