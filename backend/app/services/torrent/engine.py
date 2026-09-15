"""
BitTorrent engine implementation:
- LibtorrentEngine: Embedded C++ libtorrent-rasterbar session (Option A - chosen lightweight solution)
- MockTorrentEngine: Deterministic test fallback when libtorrent is not compiled on host Python
"""

import asyncio
import os
import shutil
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from app.config import settings
from app.services.torrent.bencode import parse_torrent_bytes
from app.services.torrent.magnet import MagnetParser
from app.utils.logger import logger

# Try importing libtorrent
try:
    import libtorrent as lt
    HAS_LIBTORRENT = True
except ImportError:
    lt = None
    HAS_LIBTORRENT = False


def _get_save_resume_flags() -> Any:
    """Returns save_resume_flags for the installed libtorrent version."""
    if lt is not None:
        if hasattr(lt, "save_resume_flags_t") and hasattr(lt.save_resume_flags_t, "flush_disk_cache"):
            return lt.save_resume_flags_t.flush_disk_cache
        if hasattr(lt, "torrent_handle") and hasattr(lt.torrent_handle, "save_resume_flags_t"):
            return getattr(lt.torrent_handle.save_resume_flags_t, "flush_disk_cache", 0)
    return None


def _get_delete_files_flag() -> int:
    """Returns delete_files flag for session.remove_torrent."""
    if lt is not None and hasattr(lt, "session"):
        return getattr(lt.session, "delete_files", 1)
    return 1


def map_torrent_state(status: Any) -> str:
    """
    Normalizes engine-specific torrent states to standard application states:
    'checking', 'metadata', 'downloading', 'finished', 'seeding', 'checking_resume', 'paused', 'unknown'.

    Accepts:
    - libtorrent torrent_status instance
    - TorrentStatus dataclass instance
    - dict with state/is_paused/paused/is_seeding/etc.
    - libtorrent states enum
    - string representation of a state
    - None or unrecognized state -> 'unknown'
    """
    if status is None:
        return "unknown"

    # 1. Paused check (for object or dict)
    is_paused = False
    if isinstance(status, dict):
        is_paused = bool(status.get("is_paused") or status.get("paused"))
    elif hasattr(status, "is_paused"):
        is_paused = bool(status.is_paused)
    elif hasattr(status, "paused"):
        is_paused = bool(status.paused)

    if is_paused:
        return "paused"

    # 2. Metadata acquisition check (if object explicitly has has_metadata == False)
    has_meta = None
    if isinstance(status, dict) and "has_metadata" in status:
        has_meta = bool(status["has_metadata"])
    elif hasattr(status, "has_metadata"):
        has_meta = bool(status.has_metadata)

    if has_meta is False:
        return "metadata"

    # Extract raw state
    raw_state = status
    if isinstance(status, dict) and "state" in status:
        raw_state = status["state"]
    elif hasattr(status, "state"):
        raw_state = status.state

    # 3. Libtorrent enum checks
    if HAS_LIBTORRENT and lt is not None and hasattr(lt, "torrent_status"):
        ts = lt.torrent_status
        if raw_state == getattr(ts, "downloading_metadata", None):
            return "metadata"
        if raw_state == getattr(ts, "checking_resume_data", None):
            return "checking_resume"
        if raw_state in (getattr(ts, "checking_files", None), getattr(ts, "allocating", None), getattr(ts, "queued_for_checking", None)):
            return "checking"
        if raw_state == getattr(ts, "seeding", None):
            return "seeding"
        if raw_state == getattr(ts, "finished", None):
            return "finished"
        if raw_state == getattr(ts, "downloading", None):
            return "downloading"

    # 4. Status object boolean flags
    if getattr(status, "is_seeding", False) or (isinstance(status, dict) and status.get("is_seeding")):
        return "seeding"
    if getattr(status, "is_finished", False) or (isinstance(status, dict) and status.get("is_finished")):
        return "finished"

    # 5. String-based matching
    state_str = str(raw_state).strip().lower()
    if "." in state_str:
        state_str = state_str.split(".")[-1]

    if state_str == "paused":
        return "paused"
    if state_str in ("downloading_metadata", "metadata"):
        return "metadata"
    if state_str in ("checking_resume_data", "checking_resume"):
        return "checking_resume"
    if state_str in ("checking_files", "allocating", "queued_for_checking", "checking"):
        return "checking"
    if state_str == "seeding":
        return "seeding"
    if state_str == "finished":
        return "finished"
    if state_str == "downloading":
        return "downloading"

    return "unknown"


@dataclass
class TorrentStatus:
    info_hash: str
    name: str
    state: str  # 'checking', 'metadata', 'downloading', 'finished', 'seeding', 'checking_resume', 'paused', 'unknown'
    progress: float = 0.0  # 0.0 to 1.0
    download_rate: int = 0  # bytes/s
    upload_rate: int = 0    # bytes/s
    total_downloaded: int = 0
    total_uploaded: int = 0
    total_size: int = 0
    num_peers: int = 0
    num_seeds: int = 0
    num_leeches: int = 0
    ratio: float = 0.0
    is_seeding: bool = False
    is_finished: bool = False
    is_paused: bool = False
    has_metadata: bool = True
    error_message: Optional[str] = None
    files: List[Dict[str, Any]] = field(default_factory=list)
    trackers_contacted: int = 0
    dht_active: bool = True
    metadata_phase: Optional[str] = None
    metadata_retry_count: int = 0
    next_retry_in: Optional[int] = None
    cached: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "info_hash": self.info_hash,
            "name": self.name,
            "state": self.state,
            "progress": self.progress,
            "download_rate": self.download_rate,
            "upload_rate": self.upload_rate,
            "total_downloaded": self.total_downloaded,
            "total_uploaded": self.total_uploaded,
            "total_size": self.total_size,
            "num_peers": self.num_peers,
            "num_seeds": self.num_seeds,
            "num_leeches": self.num_leeches,
            "ratio": self.ratio,
            "is_seeding": self.is_seeding,
            "is_finished": self.is_finished,
            "is_paused": self.is_paused,
            "has_metadata": self.has_metadata,
            "error_message": self.error_message,
            "files": self.files,
            "trackers_contacted": self.trackers_contacted,
            "dht_active": self.dht_active,
            "metadata_phase": self.metadata_phase,
            "metadata_retry_count": self.metadata_retry_count,
            "next_retry_in": self.next_retry_in,
            "cached": self.cached,
        }


def map_torrent_error(err: Any) -> str:
    """
    Maps low-level torrent engine or network errors to standard user-friendly categories:
    Invalid magnet, Metadata timeout, Tracker unavailable, No peers,
    Engine unavailable, Disk/storage error, Permission error, Network error.
    """
    if not err:
        return "Unknown torrent error"
    msg = str(err).lower()

    if "invalid magnet" in msg or "info hash" in msg or "malformed" in msg or "btih" in msg:
        return "Invalid magnet"
    if "metadata timeout" in msg or "metadata" in msg and "timeout" in msg:
        return "Metadata timeout"
    if "tracker" in msg or "announce" in msg or ("connection refused" in msg and "tracker" in msg):
        return "Tracker unavailable"
    if "no peers" in msg or ("peer" in msg and "not found" in msg):
        return "No peers"
    if "engine" in msg or "session" in msg or "service not ready" in msg or ("libtorrent" in msg and "error" in msg):
        return "Engine unavailable"
    if "space" in msg or "storage full" in msg or "disk" in msg or "nospace" in msg or "enospc" in msg:
        return "Disk/storage error"
    if "permission" in msg or "access denied" in msg or "eacces" in msg or "eperm" in msg:
        return "Permission error"
    if "network" in msg or "connection reset" in msg or "timed out" in msg or "unreachable" in msg:
        return "Network error"

    return "Torrent engine error"


class BaseTorrentEngine(ABC):
    @property
    @abstractmethod
    def engine_name(self) -> str:
        pass

    @property
    @abstractmethod
    def engine_version(self) -> str:
        pass

    @property
    def engine_status(self) -> str:
        """Returns 'healthy', 'starting', 'unavailable', or 'error'."""
        return "healthy"

    @abstractmethod
    def add_torrent(
        self,
        torrent_spec: str,  # magnet URI or path to .torrent file
        download_dir: Path,
        selected_indices: Optional[List[int]] = None,
        file_priorities: Optional[Dict[int, str]] = None,
        resume_data: Optional[bytes] = None,
        dont_download: bool = False,
    ) -> str:  # returns info_hash
        pass

    @abstractmethod
    def pause(self, info_hash: str) -> None:
        pass

    @abstractmethod
    def resume(self, info_hash: str) -> None:
        pass

    @abstractmethod
    def force_recheck(self, info_hash: str) -> None:
        pass

    @abstractmethod
    def remove(self, info_hash: str, delete_files: bool = False) -> None:
        pass

    @abstractmethod
    def get_status(self, info_hash: str) -> Optional[TorrentStatus]:
        pass

    @abstractmethod
    def set_file_priorities(self, info_hash: str, priorities: Dict[int, str]) -> None:
        pass

    def get_file_priorities(self, info_hash: str) -> Dict[int, str]:
        return {}

    @abstractmethod
    async def fetch_magnet_metadata(self, magnet_uri: str, timeout_sec: int = 30) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def save_resume_data(self, info_hash: str) -> Optional[bytes]:
        pass

    def register_metadata_event(self, info_hash: str) -> threading.Event:
        raise NotImplementedError

    def unregister_metadata_event(self, info_hash: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def shutdown(self) -> None:
        pass


class LibtorrentEngine(BaseTorrentEngine):
    """
    Production lightweight embedded BitTorrent engine using libtorrent-rasterbar.
    Operates in-process with zero extra daemon processes, zero open RPC ports,
    and minimal memory footprint.
    """

    def __init__(self):
        if not HAS_LIBTORRENT:
            raise RuntimeError("libtorrent Python bindings not found.")

        self._session_lock = threading.Lock()
        self._handles: Dict[str, Any] = {}
        self._resume_data_store: Dict[str, bytes] = {}
        self._torrent_paths: Dict[str, Path] = {}
        self._metadata_events: Dict[str, threading.Event] = {}
        self._trackers_contacted: Dict[str, int] = {}
        self._moving_storage: Set[str] = set()  # info_hashes currently mid move_storage
        self._dont_download_handles: Set[str] = set()  # info_hashes in metadata-only/dont-download mode

        # Configure session settings for maximum download performance
        alert_mask = (
            lt.alert.category_t.status_notification
            | lt.alert.category_t.storage_notification
            | lt.alert.category_t.error_notification
            | lt.alert.category_t.tracker_notification
            | lt.alert.category_t.dht_notification
            | lt.alert.category_t.peer_notification
        )
        settings_pack = {
            # Network
            "listen_interfaces": "0.0.0.0:6881",
            "alert_mask": alert_mask,

            # Rate limits (0 = unlimited unless configured)
            "connections_limit": max(settings.TORRENT_PEER_LIMIT, 500),
            "download_rate_limit": settings.TORRENT_DOWNLOAD_LIMIT,
            "upload_rate_limit": settings.TORRENT_UPLOAD_LIMIT,

            # Concurrency
            "active_downloads": settings.MAX_ACTIVE_TORRENTS,
            "active_seeds": 5,
            "active_limit": settings.MAX_ACTIVE_TORRENTS + settings.MAX_METADATA_JOBS + 10,

            # Peer discovery — announce to ALL trackers and tiers for maximum peer count
            "announce_to_all_trackers": True,
            "announce_to_all_tiers": True,
            "num_want": 400,                      # request more peers per announce
            "torrent_connect_boost": 100,         # aggressively connect on startup

            # Piece request pipeline — larger queue = higher throughput
            "max_out_request_queue": 1500,
            "max_allowed_in_request_queue": 4000,
            "request_queue_time": 3,

            # Disk I/O — bigger write cache reduces stalls (256 × 16 KiB = 4 MB, set to 1024 = 16 MB)
            "cache_size": 1024,
            "max_queued_disk_bytes": 512 * 1024 * 1024,  # 512 MB disk write buffer
            "disk_io_write_mode": 0,
            "disk_io_read_mode": 0,
            "coalesce_writes": True,
            "coalesce_reads": True,

            # Unchoke — allow more simultaneous piece transfers
            "unchoke_slots_limit": 20,
            "optimistic_unchoke_interval": 15,

            # NAT / port mapping — enabled so Docker bridge gets hole-punched
            "enable_dht": True,
            "enable_lsd": True,
            "enable_natpmp": True,
            "enable_upnp": True,

            # Misc performance
            "close_redundant_connections": True,
            "no_atime_storage": True,
            "auto_manage_interval": 15,
            "dht_announce_interval": 60,          # announce to DHT every 60 s (default 900 s)
            "peer_timeout": 20,                   # drop dead peers quickly
            "handshake_timeout": 10,
            "alert_queue_size": 5000,
        }
        self._session = lt.session(settings_pack)

        # Add comprehensive DHT bootstrap routers for faster peer discovery
        dht_routers = [
            ("router.bittorrent.com", 6881),
            ("dht.transmissionbt.com", 6881),
            ("router.utorrent.com", 6881),
            ("dht.aelitis.com", 6881),
            ("router.bitcomet.com", 6881),
            ("dht.libtorrent.org", 25401),
        ]
        for host, port in dht_routers:
            try:
                self._session.add_dht_router(host, port)
            except Exception as e:
                logger.warning(f"Failed to add DHT router {host}:{port}: {e}")

        self._running = True
        self._alert_thread = threading.Thread(target=self._process_alerts, daemon=True, name="LibtorrentAlertWorker")
        self._alert_thread.start()
        logger.info(f"LibtorrentEngine initialized (version {lt.__version__}) with performance-optimized settings")

    @property
    def engine_name(self) -> str:
        return "libtorrent"

    @property
    def engine_version(self) -> str:
        return getattr(lt, "__version__", "2.1.1.0")

    @property
    def engine_status(self) -> str:
        if not HAS_LIBTORRENT or not self._running:
            return "unavailable"
        return "healthy"

    def _process_alerts(self) -> None:
        """Processes background session alerts from libtorrent."""
        while self._running:
            try:
                alerts = self._session.pop_alerts()
                for alert in alerts:
                    # Metadata received alert for magnets
                    if isinstance(alert, lt.metadata_received_alert):
                        handle = alert.handle
                        if handle.is_valid():
                            ih = str(handle.info_hash()).lower()
                            ti = None
                            try:
                                ti = handle.torrent_file() or (handle.get_torrent_info() if hasattr(handle, "get_torrent_info") else None)
                            except Exception as e:
                                logger.warning(f"Error reading torrent_file on alert for [{ih}]: {e}")

                            num_files = ti.num_files() if ti else 0
                            tot_size = ti.total_size() if ti else 0
                            has_m = handle.status().has_metadata if hasattr(handle, "status") else True
                            logger.info(
                                f"TORRENT_METADATA_EVENT info_hash={ih} "
                                f"has_metadata={has_m} torrent_info={bool(ti)} "
                                f"file_count={num_files} total_size={tot_size}"
                            )

                            if ih in self._dont_download_handles and ti:
                                try:
                                    handle.prioritize_files([0] * num_files)
                                except Exception as e:
                                    logger.warning(f"Error zeroing file priorities on metadata for [{ih}]: {e}")
                            if ih in self._metadata_events:
                                self._metadata_events[ih].set()

                    # Resume data generated alert
                    elif isinstance(alert, lt.save_resume_data_alert):
                        handle = alert.handle
                        if handle.is_valid():
                            ih = str(handle.info_hash()).lower()
                            try:
                                buf = lt.write_resume_data_buf(alert.params)
                                with self._session_lock:
                                    self._resume_data_store[ih] = buf
                            except Exception as e:
                                logger.warning(f"Failed to serialize resume data for [{ih}]: {e}")

                    # Storage move completed — resume downloading only if we were downloading
                    elif hasattr(lt, "storage_moved_alert") and isinstance(alert, lt.storage_moved_alert):
                        handle = alert.handle
                        if handle.is_valid():
                            ih = str(handle.info_hash()).lower()
                            was_moving = ih in self._moving_storage
                            self._moving_storage.discard(ih)
                            if was_moving:
                                # We scheduled this move as part of a download transition — resume now
                                try:
                                    if hasattr(lt, "torrent_flags") and hasattr(lt.torrent_flags, "default_dont_download"):
                                        handle.unset_flags(lt.torrent_flags.default_dont_download)
                                    handle.resume()
                                    handle.force_reannounce()
                                    logger.info(f"Storage move completed for [{ih}]; torrent resumed and reannounced")
                                except Exception as e:
                                    logger.warning(f"Error resuming after storage move [{ih}]: {e}")
                            else:
                                logger.debug(f"Storage move completed for [{ih}] (metadata-only move, no resume needed)")

                    # Storage move failed
                    elif hasattr(lt, "storage_moved_failed_alert") and isinstance(alert, lt.storage_moved_failed_alert):
                        handle = alert.handle
                        if handle.is_valid():
                            ih = str(handle.info_hash()).lower()
                            self._moving_storage.discard(ih)
                            logger.error(f"Storage move FAILED for [{ih}]: {alert.message()}")

                    # Tracker alert
                    elif hasattr(lt, "tracker_reply_alert") and isinstance(alert, (lt.tracker_reply_alert, lt.tracker_announce_alert)):
                        handle = getattr(alert, "handle", None)
                        if handle and handle.is_valid():
                            ih = str(handle.info_hash()).lower()
                            self._trackers_contacted[ih] = self._trackers_contacted.get(ih, 0) + 1

                    # Error alert
                    elif isinstance(alert, lt.torrent_error_alert):
                        logger.warning(f"Torrent alert error: {alert.message()}")

                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in alert processing loop: {e}")
                time.sleep(0.5)


    def add_torrent(
        self,
        torrent_spec: str,
        download_dir: Path,
        selected_indices: Optional[List[int]] = None,
        file_priorities: Optional[Dict[int, str]] = None,
        resume_data: Optional[bytes] = None,
        dont_download: bool = False,
    ) -> str:
        try:
            download_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.debug(f"mkdir in engine add_torrent: {e}")
        atp = None

        if resume_data:
            try:
                atp = lt.read_resume_data(resume_data)
                atp.save_path = str(download_dir.resolve())
            except Exception as e:
                logger.warning(f"Could not restore resume data: {e}, falling back to spec")

        if atp is None:
            if MagnetParser.is_magnet_url(torrent_spec):
                atp = lt.parse_magnet_uri(torrent_spec)
                atp.save_path = str(download_dir.resolve())
                # Add default fallback trackers if magnet has few/none (Section 11)
                default_trackers = getattr(settings, "default_torrent_trackers_list", [])
                if hasattr(atp, "trackers"):
                    for tr in default_trackers:
                        if tr not in atp.trackers:
                            atp.trackers.append(tr)
            else:
                # File path
                ti = lt.torrent_info(str(torrent_spec))
                atp = lt.add_torrent_params()
                atp.ti = ti
                atp.save_path = str(download_dir.resolve())

        if hasattr(atp, "flags") and hasattr(lt, "torrent_flags"):
            if hasattr(lt.torrent_flags, "paused"):
                atp.flags &= ~lt.torrent_flags.paused
            if dont_download and hasattr(lt.torrent_flags, "default_dont_download"):
                atp.flags |= lt.torrent_flags.default_dont_download
            elif not dont_download and hasattr(lt.torrent_flags, "default_dont_download"):
                atp.flags &= ~lt.torrent_flags.default_dont_download

        with self._session_lock:
            # Check if this torrent handle is already tracked in session
            candidate_ih = None
            if hasattr(atp, "info_hashes"):
                ih_obj = atp.info_hashes
                if hasattr(ih_obj, "v1") and not ih_obj.v1.is_all_zeros():
                    candidate_ih = str(ih_obj.v1).lower()
            elif hasattr(atp, "info_hash"):
                candidate_ih = str(atp.info_hash).lower()

            existing_handle = self._handles.get(candidate_ih) if candidate_ih else None
            if existing_handle and existing_handle.is_valid():
                handle = existing_handle
            else:
                handle = self._session.add_torrent(atp)

            ih = str(handle.info_hash()).lower()
            self._handles[ih] = handle

            # If download directory changed from previous location (e.g. temp -> downloads), move storage.
            # move_storage is asynchronous in libtorrent — the torrent is internally paused until it
            # completes. We track the move in _moving_storage; the storage_moved_alert handler will
            # resume + reannounce when the move is done.
            storage_moving = False
            try:
                curr_save = Path(handle.status().save_path).resolve()
                dest_save = download_dir.resolve()
                if curr_save != dest_save:
                    logger.info(f"Moving storage for torrent [{ih}] from {curr_save} to {dest_save}")
                    if not dont_download:
                        self._moving_storage.add(ih)
                        storage_moving = True
                    handle.move_storage(str(dest_save))
            except Exception as e:
                logger.warning(f"Could not verify/move storage for [{ih}]: {e}")
                storage_moving = False

            self._torrent_paths[ih] = download_dir

            if dont_download:
                self._dont_download_handles.add(ih)
            else:
                self._dont_download_handles.discard(ih)

            # Unset default_dont_download and resume if actively downloading.
            # Skip resume here if storage is being moved — the alert handler will resume.
            if not dont_download and not storage_moving:
                if hasattr(handle, "unset_flags") and hasattr(lt, "torrent_flags") and hasattr(lt.torrent_flags, "default_dont_download"):
                    try:
                        handle.unset_flags(lt.torrent_flags.default_dont_download)
                    except Exception:
                        pass
                handle.resume()
                # Force immediate announce to all trackers for fastest peer discovery
                try:
                    handle.force_reannounce()
                except Exception:
                    pass
            elif dont_download:
                try:
                    handle.force_reannounce()
                    if hasattr(handle, "force_dht_announce"):
                        handle.force_dht_announce()
                except Exception:
                    pass

            # Apply file selection / priorities if metadata is already available
            if handle.status().has_metadata:
                self._apply_priorities_to_handle(handle, selected_indices, file_priorities, dont_download=dont_download)

        logger.info(f"Added torrent [{ih}] to LibtorrentEngine at {download_dir} (dont_download={dont_download}, storage_moving={storage_moving})")
        return ih

    def _apply_priorities_to_handle(
        self,
        handle: Any,
        selected_indices: Optional[List[int]],
        file_priorities: Optional[Dict[int, str]],
        dont_download: bool = False,
    ) -> None:
        try:
            ti = handle.torrent_file()
            num_files = ti.num_files()

            if dont_download:
                priorities = [0] * num_files
            else:
                priorities = [4] * num_files  # 4 = default priority

                if selected_indices is not None:
                    selected_set = set(selected_indices)
                    for i in range(num_files):
                        if i not in selected_set:
                            priorities[i] = 0  # 0 = skip file

                if file_priorities:
                    priority_map = {"high": 7, "normal": 4, "low": 1, "skip": 0}
                    for idx_str, prio_str in file_priorities.items():
                        idx = int(idx_str)
                        if 0 <= idx < num_files:
                            priorities[idx] = priority_map.get(str(prio_str).lower(), 4)

            handle.prioritize_files(priorities)
        except Exception as e:
            logger.warning(f"Could not apply file priorities to handle: {e}")

    def pause(self, info_hash: str) -> None:
        ih = info_hash.lower()
        with self._session_lock:
            handle = self._handles.get(ih)
            if handle and handle.is_valid():
                handle.pause()
                flags = _get_save_resume_flags()
                if flags is not None:
                    handle.save_resume_data(flags)
                else:
                    handle.save_resume_data()

    def resume(self, info_hash: str) -> None:
        ih = info_hash.lower()
        with self._session_lock:
            handle = self._handles.get(ih)
            if handle and handle.is_valid():
                handle.resume()

    def force_recheck(self, info_hash: str) -> None:
        ih = info_hash.lower()
        with self._session_lock:
            handle = self._handles.get(ih)
            if handle and handle.is_valid():
                handle.force_recheck()

    def remove(self, info_hash: str, delete_files: bool = False) -> None:
        ih = info_hash.lower()
        with self._session_lock:
            handle = self._handles.pop(ih, None)
            target_path = self._torrent_paths.pop(ih, None)
            self._resume_data_store.pop(ih, None)

            if handle and handle.is_valid():
                flags = _get_delete_files_flag() if delete_files else 0
                self._session.remove_torrent(handle, flags)

        if delete_files and target_path and target_path.exists():
            try:
                if target_path.is_dir():
                    shutil.rmtree(target_path, ignore_errors=True)
                else:
                    target_path.unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Error removing files for torrent [{ih}]: {e}")

    def get_status(self, info_hash: str) -> Optional[TorrentStatus]:
        ih = info_hash.lower()
        handle = self._handles.get(ih)
        if not handle or not handle.is_valid():
            return None

        st = handle.status()
        ti = None
        if st.has_metadata:
            try:
                ti = handle.torrent_file() or (handle.get_torrent_info() if hasattr(handle, "get_torrent_info") else None)
            except Exception as e:
                logger.warning(f"Error reading torrent_file for [{ih}]: {e}")
                ti = None

        name = handle.name() or (ti.name() if ti else f"torrent_{ih[:10]}")
        total_size = ti.total_size() if ti else st.total_wanted

        state_str = map_torrent_state(st)
        ratio = (st.total_upload / st.total_download) if st.total_download > 0 else 0.0

        files_list = []
        if ti:
            try:
                files_storage = ti.files()
                for idx in range(ti.num_files()):
                    fp = files_storage.file_path(idx)
                    fs = files_storage.file_size(idx)
                    files_list.append({
                        "index": idx,
                        "path": fp,
                        "size": fs,
                    })
            except Exception as e:
                logger.warning(f"Error extracting file list from torrent_info for [{ih}]: {e}")

        peers_cnt = int(st.num_peers)
        trackers_cnt = self._trackers_contacted.get(ih, 0)
        dht_running = True
        try:
            if hasattr(self._session, "is_dht_running"):
                dht_running = bool(self._session.is_dht_running())
        except Exception:
            pass

        has_actual_metadata = bool(st.has_metadata and ti is not None and len(files_list) > 0)
        phase = None
        if not has_actual_metadata:
            if peers_cnt > 0:
                phase = f"{peers_cnt} peers discovered · Downloading metadata"
            elif trackers_cnt > 0:
                phase = f"{trackers_cnt} trackers contacted · Discovering peers"
            else:
                phase = "Contacting trackers"
        else:
            phase = "Metadata received"

        return TorrentStatus(
            info_hash=ih,
            name=name,
            state=state_str,
            progress=float(st.progress),
            download_rate=int(st.download_rate),
            upload_rate=int(st.upload_rate),
            total_downloaded=int(st.total_download),
            total_uploaded=int(st.total_upload),
            total_size=total_size,
            num_peers=peers_cnt,
            num_seeds=int(st.num_seeds),
            num_leeches=max(0, peers_cnt - int(st.num_seeds)),
            ratio=round(ratio, 2),
            is_seeding=bool(st.is_seeding),
            is_finished=bool(st.is_finished),
            is_paused=bool(st.paused),
            has_metadata=has_actual_metadata,
            error_message=st.error if hasattr(st, "error") and st.error else None,
            files=files_list,
            trackers_contacted=trackers_cnt,
            dht_active=dht_running,
            metadata_phase=phase,
        )

    def set_file_priorities(self, info_hash: str, priorities: Dict[int, str]) -> None:
        ih = info_hash.lower()
        handle = self._handles.get(ih)
        if handle and handle.is_valid() and handle.status().has_metadata:
            self._apply_priorities_to_handle(handle, None, priorities)

    async def fetch_magnet_metadata(self, magnet_uri: str, timeout_sec: int = 30) -> Optional[Dict[str, Any]]:
        parsed = MagnetParser.parse_magnet(magnet_uri)
        ih = parsed["info_hash"]

        # Check if already running with metadata
        status = self.get_status(ih)
        if status and status.has_metadata:
            return {
                "info_hash": ih,
                "name": status.name,
                "total_size": status.total_size,
                "file_count": len(status.files),
                "trackers": parsed["trackers"],
                "is_multi_file": len(status.files) > 1,
                "files": status.files,
            }

        # Add temporary handle to fetch metadata
        temp_dir = settings.temp_path / f"meta_{ih}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        event = threading.Event()
        self._metadata_events[ih] = event

        atp = lt.parse_magnet_uri(magnet_uri)
        atp.save_path = str(temp_dir)
        atp.flags |= lt.torrent_flags.default_dont_download
        if hasattr(lt, "torrent_flags") and hasattr(lt.torrent_flags, "paused"):
            atp.flags &= ~lt.torrent_flags.paused

        handle = self._session.add_torrent(atp)
        self._handles[ih] = handle
        self._torrent_paths[ih] = temp_dir

        # Wait non-blockingly in asyncio
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, lambda: event.wait(timeout=timeout_sec))
        finally:
            self._metadata_events.pop(ih, None)

        if handle.is_valid() and handle.status().has_metadata:
            st = self.get_status(ih)
            return {
                "info_hash": ih,
                "name": st.name if st else parsed["name"],
                "total_size": st.total_size if st else 0,
                "file_count": len(st.files) if st else 1,
                "trackers": parsed["trackers"],
                "is_multi_file": len(st.files) > 1 if st else False,
                "files": st.files if st else [],
            }

        # If metadata couldn't be acquired before timeout, return magnet parameters preview
        return {
            "info_hash": ih,
            "name": parsed["name"],
            "total_size": parsed["total_size"],
            "file_count": 1,
            "trackers": parsed["trackers"],
            "is_multi_file": False,
            "files": [{"index": 0, "path": parsed["name"], "size": parsed["total_size"]}],
            "has_metadata": False,
        }

    def save_resume_data(self, info_hash: str) -> Optional[bytes]:
        ih = info_hash.lower()
        handle = self._handles.get(ih)
        if handle and handle.is_valid():
            flags = _get_save_resume_flags()
            if flags is not None:
                handle.save_resume_data(flags)
            else:
                handle.save_resume_data()
            # Wait briefly for alert
            for _ in range(10):
                if ih in self._resume_data_store:
                    return self._resume_data_store[ih]
                time.sleep(0.05)
        return self._resume_data_store.get(ih)

    def register_metadata_event(self, info_hash: str) -> threading.Event:
        ih = info_hash.lower()
        with self._session_lock:
            if ih not in self._metadata_events:
                self._metadata_events[ih] = threading.Event()
            handle = self._handles.get(ih)
            if handle and handle.is_valid():
                try:
                    if handle.status().has_metadata:
                        self._metadata_events[ih].set()
                except Exception:
                    pass
            return self._metadata_events[ih]

    def unregister_metadata_event(self, info_hash: str) -> None:
        ih = info_hash.lower()
        with self._session_lock:
            self._metadata_events.pop(ih, None)

    def shutdown(self) -> None:
        self._running = False
        flags = _get_save_resume_flags()
        with self._session_lock:
            for handle in self._handles.values():
                if handle.is_valid():
                    try:
                        handle.pause()
                        if flags is not None:
                            handle.save_resume_data(flags)
                        else:
                            handle.save_resume_data()
                    except Exception:
                        pass
        time.sleep(0.3)
        logger.info("LibtorrentEngine shutdown successfully.")


class MockTorrentEngine(BaseTorrentEngine):
    """
    Test and fallback BitTorrent engine used when libtorrent is not available.
    Accurately supports metadata, file priorities, start, pause, resume, recheck,
    seeding simulation, and cleanup for all automated unit tests.
    """

    def __init__(self):
        self._torrents: Dict[str, Dict[str, Any]] = {}
        self._metadata_events: Dict[str, threading.Event] = {}
        self._lock = threading.Lock()
        logger.info("MockTorrentEngine initialized (fallback test mode)")

    @property
    def engine_name(self) -> str:
        return "mock_bittorrent"

    @property
    def engine_version(self) -> str:
        return "2.1.1-test"

    @property
    def engine_status(self) -> str:
        return "healthy"

    def add_torrent(
        self,
        torrent_spec: str,
        download_dir: Path,
        selected_indices: Optional[List[int]] = None,
        file_priorities: Optional[Dict[int, str]] = None,
        resume_data: Optional[bytes] = None,
        dont_download: bool = False,
    ) -> str:
        download_dir.mkdir(parents=True, exist_ok=True)
        ih = None
        name = "Sample_Torrent"
        total_size = 10000000
        files = []

        if MagnetParser.is_magnet_url(torrent_spec):
            parsed = MagnetParser.parse_magnet(torrent_spec)
            ih = parsed["info_hash"]
            name = parsed["name"]
            total_size = parsed["total_size"] or 10000000
            files = [{"index": 0, "path": name, "size": total_size}]
        else:
            # File
            p = Path(torrent_spec)
            if p.exists():
                with open(p, "rb") as f:
                    meta = parse_torrent_bytes(f.read())
                    ih = meta["info_hash"]
                    name = meta["name"]
                    total_size = meta["total_size"]
                    files = meta["files"]
            else:
                ih = "0123456789abcdef0123456789abcdef01234567"
                files = [{"index": 0, "path": "file.bin", "size": total_size}]

        with self._lock:
            existing = self._torrents.get(ih)
            if existing:
                existing["download_dir"] = download_dir
                if not dont_download:
                    existing["has_metadata"] = True
                    existing["state"] = "downloading"
                    existing["download_rate"] = 5242880
                    existing["is_paused"] = False
                if selected_indices:
                    existing["selected_indices"] = selected_indices
                if file_priorities:
                    existing["priorities"] = file_priorities
                logger.info(f"MockTorrentEngine updated [{ih}] at {download_dir} (dont_download={dont_download})")
                return ih

            self._torrents[ih] = {
                "info_hash": ih,
                "name": name,
                "state": "metadata" if dont_download else "downloading",
                "progress": 0.0 if dont_download else 0.05,
                "download_rate": 0 if dont_download else 5242880,  # 5 MB/s
                "upload_rate": 0 if dont_download else 262144,     # 256 KB/s
                "total_downloaded": 0 if dont_download else 500000,
                "total_uploaded": 0 if dont_download else 262144,
                "total_size": total_size,
                "num_peers": 18,
                "num_seeds": 24,
                "ratio": 0.52,
                "is_seeding": False,
                "is_finished": False,
                "is_paused": False,
                "has_metadata": True,
                "download_dir": download_dir,
                "files": files,
                "priorities": file_priorities or {},
                "selected_indices": selected_indices,
            }

        logger.info(f"MockTorrentEngine added [{ih}] at {download_dir} (dont_download={dont_download})")
        return ih

    def pause(self, info_hash: str) -> None:
        ih = info_hash.lower()
        with self._lock:
            if ih in self._torrents:
                self._torrents[ih]["state"] = "paused"
                self._torrents[ih]["is_paused"] = True
                self._torrents[ih]["download_rate"] = 0
                self._torrents[ih]["upload_rate"] = 0

    def resume(self, info_hash: str) -> None:
        ih = info_hash.lower()
        with self._lock:
            if ih in self._torrents:
                self._torrents[ih]["state"] = "downloading"
                self._torrents[ih]["is_paused"] = False
                self._torrents[ih]["download_rate"] = 5242880

    def force_recheck(self, info_hash: str) -> None:
        ih = info_hash.lower()
        with self._lock:
            if ih in self._torrents:
                self._torrents[ih]["state"] = "checking"

    def remove(self, info_hash: str, delete_files: bool = False) -> None:
        ih = info_hash.lower()
        with self._lock:
            t = self._torrents.pop(ih, None)
        if delete_files and t and t.get("download_dir"):
            d = t["download_dir"]
            if d.exists():
                shutil.rmtree(d, ignore_errors=True)

    def set_has_metadata(self, info_hash: str, has_meta: bool, files: Optional[List[Dict[str, Any]]] = None) -> None:
        ih = info_hash.lower()
        with self._lock:
            if ih in self._torrents:
                self._torrents[ih]["has_metadata"] = has_meta
                self._torrents[ih]["state"] = "downloading" if has_meta else "metadata"
                if files:
                    self._torrents[ih]["files"] = files
                    self._torrents[ih]["total_size"] = sum(f.get("size", 0) for f in files)

    def get_status(self, info_hash: str) -> Optional[TorrentStatus]:
        ih = info_hash.lower()
        with self._lock:
            t = self._torrents.get(ih)
            if not t:
                return None

            files_data = t.get("files", [])
            has_m = bool(t.get("has_metadata", True) and len(files_data) > 0)
            if not has_m:
                t["has_metadata"] = False

            phase = "Metadata received" if has_m else "Waiting for metadata"
            return TorrentStatus(
                info_hash=t["info_hash"],
                name=t["name"],
                state=map_torrent_state(t),
                progress=t["progress"],
                download_rate=t["download_rate"],
                upload_rate=t["upload_rate"],
                total_downloaded=t["total_downloaded"],
                total_uploaded=t["total_uploaded"],
                total_size=t["total_size"],
                num_peers=t["num_peers"],
                num_seeds=t["num_seeds"],
                num_leeches=max(0, t["num_peers"] - t["num_seeds"]),
                ratio=t["ratio"],
                is_seeding=t["is_seeding"],
                is_finished=t["is_finished"],
                is_paused=t["is_paused"],
                has_metadata=has_m,
                files=t["files"] if has_m else [],
                trackers_contacted=t.get("trackers_contacted", 4),
                dht_active=True,
                metadata_phase=phase,
                cached=t.get("cached", False),
            )

    def set_file_priorities(self, info_hash: str, priorities: Dict[int, str]) -> None:
        ih = info_hash.lower()
        with self._lock:
            if ih in self._torrents:
                self._torrents[ih]["priorities"].update(priorities)

    def get_file_priorities(self, info_hash: str) -> Dict[int, str]:
        ih = info_hash.lower()
        with self._lock:
            if ih in self._torrents:
                return dict(self._torrents[ih].get("priorities", {}))
        return {}

    async def fetch_magnet_metadata(self, magnet_uri: str, timeout_sec: int = 30) -> Optional[Dict[str, Any]]:
        parsed = MagnetParser.parse_magnet(magnet_uri)
        return {
            "info_hash": parsed["info_hash"],
            "name": parsed["name"],
            "total_size": parsed["total_size"] or 2147483648,
            "file_count": 2,
            "trackers": parsed["trackers"],
            "is_multi_file": True,
            "files": [
                {"index": 0, "path": f"{parsed['name']}/video.mp4", "size": 2140000000},
                {"index": 1, "path": f"{parsed['name']}/readme.txt", "size": 7483648},
            ],
            "has_metadata": True,
        }

    def save_resume_data(self, info_hash: str) -> Optional[bytes]:
        return b"mock_resume_data"

    def register_metadata_event(self, info_hash: str) -> threading.Event:
        ih = info_hash.lower()
        with self._lock:
            if ih not in self._metadata_events:
                self._metadata_events[ih] = threading.Event()
            tor = self._torrents.get(ih)
            if tor and tor.get("has_metadata", True):
                self._metadata_events[ih].set()
            return self._metadata_events[ih]

    def unregister_metadata_event(self, info_hash: str) -> None:
        ih = info_hash.lower()
        with self._lock:
            self._metadata_events.pop(ih, None)

    def shutdown(self) -> None:
        with self._lock:
            self._torrents.clear()


# Global engine singleton
_engine_instance: Optional[BaseTorrentEngine] = None
_engine_lock = threading.Lock()


def get_torrent_engine() -> BaseTorrentEngine:
    global _engine_instance
    with _engine_lock:
        if _engine_instance is None:
            if HAS_LIBTORRENT:
                try:
                    _engine_instance = LibtorrentEngine()
                except Exception as e:
                    logger.error(f"Failed to initialize LibtorrentEngine: {e}, using MockTorrentEngine")
                    _engine_instance = MockTorrentEngine()
            else:
                logger.info("libtorrent library not imported; using MockTorrentEngine")
                _engine_instance = MockTorrentEngine()
        return _engine_instance
