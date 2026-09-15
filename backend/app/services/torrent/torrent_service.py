"""
TorrentService: Orchestrates BitTorrent downloads, magnet resolution,
file selection, background polling, seeding policies, and Media Library indexing.
"""

import asyncio
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from app.config import settings
from app.models.job import Job
from app.models.schemas import (
    AnalyzeResponse,
    JobStatus,
    TorrentAnalysisResponse,
    TorrentDownloadConfig,
    TorrentFileItem,
    TorrentMetadataResponse,
    TorrentTelemetry,
)
from app.repositories.job_repository import JobRepository
from app.repositories.media_repository import MediaRepository
from app.repositories.torrent_repository import TorrentRepository
from app.services.duplicate_detector import DuplicateDetector
from app.services.file_service import FileService
from app.services.torrent.bencode import parse_torrent_bytes
from app.services.torrent.detector import InputDetector
from app.services.torrent.engine import BaseTorrentEngine, TorrentStatus, get_torrent_engine, map_torrent_error, map_torrent_state
from app.services.torrent.magnet import MagnetParser, MagnetValidator
from app.services.torrent.metadata_cache import MetadataCache
from app.services.webhook_service import WebhookService
from app.utils.errors import (
    FileTooLargeError,
    InvalidMagnetError,
    StorageFullError,
    TorrentEngineUnavailableError,
    TorrentException,
    TorrentMetadataUnavailableError,
    ValidationError,
)
from app.utils.formatting import format_bytes
from app.utils.logger import logger

# Supported media extensions for automatic library cataloging
MEDIA_EXTENSIONS = {
    ".mp4", ".mkv", ".webm", ".avi", ".mov", ".m4v",
    ".mp3", ".flac", ".m4a", ".wav", ".ogg", ".opus",
}


class TorrentService:
    def __init__(self):
        self._engine: Optional[BaseTorrentEngine] = None
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
        self._metadata_semaphore = asyncio.Semaphore(settings.MAX_METADATA_JOBS)
        self._download_semaphore = asyncio.Semaphore(settings.MAX_ACTIVE_TORRENTS)

    @property
    def engine(self) -> BaseTorrentEngine:
        if self._engine is None:
            self._engine = get_torrent_engine()
        return self._engine

    async def initialize(self) -> None:
        """Restores persistent torrent sessions upon application startup / container restart."""
        logger.info("Initializing TorrentService and recovering active sessions...")
        try:
            active_torrents = TorrentRepository.list_active()
            torrent_base = settings.torrent_storage_path if hasattr(settings, "torrent_storage_path") and settings.torrent_storage_path else settings.download_path
            for tor in active_torrents:
                ih = tor["info_hash"]
                down_dir = Path(tor["download_dir"]) if tor.get("download_dir") else torrent_base / tor["name"]
                spec = tor.get("torrent_file_path") or tor.get("magnet_uri")
                if not spec:
                    continue

                # Look for saved resume data
                resume_file = settings.torrent_metadata_path / f"{ih}.fastresume"
                resume_bytes = None
                if resume_file.exists():
                    try:
                        resume_bytes = resume_file.read_bytes()
                    except Exception:
                        pass

                try:
                    self.engine.add_torrent(
                        torrent_spec=spec,
                        download_dir=down_dir,
                        resume_data=resume_bytes,
                    )
                    # If paused, ensure engine pauses handle
                    if tor["status"] == "PAUSED":
                        self.engine.pause(ih)
                    logger.info(f"Recovered torrent session [{ih}] ({tor['name']})")
                except Exception as e:
                    logger.warning(f"Could not restore torrent session [{ih}]: {e}")
        except Exception as e:
            logger.error(f"Error during TorrentService initialization: {e}")

    def shutdown(self) -> None:
        """Gracefully shuts down torrent engine and flushes resume data."""
        logger.info("Shutting down TorrentService...")
        # Save resume data for all active torrents
        try:
            for tor in TorrentRepository.list_active():
                ih = tor["info_hash"]
                buf = self.engine.save_resume_data(ih)
                if buf:
                    resume_file = settings.torrent_metadata_path / f"{ih}.fastresume"
                    try:
                        resume_file.write_bytes(buf)
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Error saving fastresume data on shutdown: {e}")

        if self._engine:
            self._engine.shutdown()

    async def analyze_input(self, input_data: str) -> TorrentAnalysisResponse:
        """
        Inspects metadata for a magnet URI or .torrent file path/buffer.
        Returns a TorrentAnalysisResponse.
        """
        itype = InputDetector.detect(input_data)
        if itype == "torrent_magnet":
            return await self.analyze_magnet(input_data)
        elif itype == "torrent_file":
            return await self.analyze_torrent_file(input_data)
        else:
            raise ValidationError(f"Invalid torrent input: {input_data[:50]}")

    async def analyze_magnet(self, magnet_uri: str) -> TorrentAnalysisResponse:
        """
        Analyzes a BitTorrent magnet link.
        Uses MagnetValidator for dedicated scheme/parameter validation.
        Retrieves metadata and returns structured TorrentAnalysisResponse.
        """
        parsed = MagnetValidator.validate(magnet_uri)
        ih = parsed["info_hash"]
        name = parsed["name"]

        if not self.engine:
            raise TorrentEngineUnavailableError("The BitTorrent service is not currently ready.")

        logger.info(
            "torrent_metadata_requested",
            extra={
                "info_hash": ih,
                "trackers_count": len(parsed.get("trackers", [])),
                "has_display_name": bool(name and name != f"torrent_{ih[:8]}"),
            },
        )

        # 1. Fast Cache Check (Section 24, 25, 27)
        meta = MetadataCache.get(ih)
        has_meta = False
        if meta and meta.get("files"):
            has_meta = True
            logger.info(f"Metadata cache hit for torrent [{ih}] ({meta.get('name')})")
        else:
            # 2. Check if engine already has an active session with metadata
            status = self.engine.get_status(ih) if self._engine else None
            if status and status.has_metadata and status.files:
                has_meta = True
                meta = {
                    "info_hash": ih,
                    "name": status.name,
                    "total_size": status.total_size,
                    "file_count": len(status.files),
                    "files": status.files,
                    "trackers": parsed["trackers"],
                    "has_metadata": True,
                }

        files_list: List[TorrentFileItem] = []
        if has_meta and meta and meta.get("files"):
            for idx, f in enumerate(meta["files"]):
                sz = f.get("size", 0)
                files_list.append(
                    TorrentFileItem(
                        index=f.get("index", idx),
                        path=f.get("path", f"file_{idx}"),
                        size=sz,
                        size_formatted=format_bytes(sz),
                        selected=True,
                        priority="normal",
                    )
                )

        total_size = meta.get("total_size", 0) if (meta and has_meta) else None
        has_display_name = bool(name and not name.startswith("magnet_") and not name.startswith("torrent_"))
        resolved_name = (meta.get("name") if (meta and has_meta and meta.get("name")) else (name if has_display_name else None))
        status_str = "ready" if has_meta else "metadata_pending"

        logger.info(
            "torrent_metadata_received",
            extra={
                "info_hash": ih,
                "has_metadata": has_meta,
                "total_size": total_size,
                "files_count": len(files_list),
            },
        )

        t_meta = TorrentMetadataResponse(
            info_hash=ih,
            name=resolved_name or name or f"magnet_{ih[:10]}",
            total_size=total_size or 0,
            total_size_formatted=format_bytes(total_size) if (total_size and total_size > 0) else "Unknown",
            file_count=len(files_list) if files_list else 1,
            trackers=parsed["trackers"],
            is_multi_file=len(files_list) > 1,
            files=files_list,
            has_metadata=has_meta,
            magnet_uri=magnet_uri,
        )

        found_job_id = None
        try:
            from app.services.job_manager import job_manager
            for j in job_manager._jobs.values():
                if getattr(j, "info_hash", None) == ih and not j.is_cancelled:
                    found_job_id = j.id
                    break
        except Exception:
            pass

        return TorrentAnalysisResponse(
            type="torrent",
            input_type="magnet",
            status=status_str,
            info_hash=ih,
            name=resolved_name,
            total_size=total_size if (total_size and total_size > 0) else None,
            total_size_formatted=format_bytes(total_size) if (total_size and total_size > 0) else None,
            file_count=len(files_list),
            files=files_list,
            trackers=parsed["trackers"],
            magnet_uri=magnet_uri,
            url=magnet_uri,
            title=resolved_name or f"magnet_{ih[:10]}",
            torrent_info=t_meta,
            extractor="torrent:magnet",
            media_type="torrent",
            is_torrent=True,
            provider="torrent",
            job_id=found_job_id,
        )

    async def _analyze_magnet(self, magnet_uri: str) -> TorrentAnalysisResponse:
        return await self.analyze_magnet(magnet_uri)

    async def analyze_torrent_file(self, file_path_or_spec: str) -> TorrentAnalysisResponse:
        p = Path(file_path_or_spec)
        if not p.exists():
            raise ValidationError(f"Torrent file not found: {file_path_or_spec}")

        content = p.read_bytes()
        meta = parse_torrent_bytes(content)
        ih = meta["info_hash"]

        files_list: List[TorrentFileItem] = []
        for idx, f in enumerate(meta["files"]):
            sz = f["size"]
            files_list.append(
                TorrentFileItem(
                    index=f["index"],
                    path=f["path"],
                    size=sz,
                    size_formatted=format_bytes(sz),
                    selected=True,
                    priority="normal",
                )
            )

        t_meta = TorrentMetadataResponse(
            info_hash=ih,
            name=meta["name"],
            total_size=meta["total_size"],
            total_size_formatted=format_bytes(meta["total_size"]),
            file_count=len(files_list),
            piece_count=meta["piece_count"],
            piece_length=meta["piece_length"],
            trackers=meta["trackers"],
            created_date=meta["creation_date"],
            comment=meta["comment"],
            is_multi_file=meta["is_multi_file"],
            files=files_list,
            has_metadata=True,
        )

        return TorrentAnalysisResponse(
            type="torrent",
            input_type="torrent_file",
            status="ready",
            info_hash=ih,
            name=meta["name"],
            total_size=meta["total_size"],
            total_size_formatted=format_bytes(meta["total_size"]),
            file_count=len(files_list),
            files=files_list,
            trackers=meta["trackers"],
            magnet_uri=None,
            url=f"file://{p.resolve()}",
            title=t_meta.name,
            torrent_info=t_meta,
            extractor="torrent:file",
            media_type="torrent",
            is_torrent=True,
            provider="torrent",
        )

    async def _analyze_torrent_file(self, file_path_or_spec: str) -> TorrentAnalysisResponse:
        return await self.analyze_torrent_file(file_path_or_spec)

    async def handle_torrent_upload(self, filename: str, file_bytes: bytes) -> Tuple[str, TorrentMetadataResponse]:
        """Handles upload of .torrent file and parses metadata."""
        return await self.save_uploaded_torrent(file_bytes=file_bytes, original_filename=filename)

    async def save_uploaded_torrent(self, file_bytes: bytes, original_filename: str = "torrent", filename: Optional[str] = None) -> Tuple[str, TorrentMetadataResponse]:
        """Validates and stores an uploaded .torrent file."""
        fname = filename or original_filename
        if len(file_bytes) > settings.max_torrent_file_size_bytes:
            raise FileTooLargeError(
                f"Uploaded .torrent file size ({format_bytes(len(file_bytes))}) exceeds maximum allowed ({settings.MAX_TORRENT_FILE_SIZE})."
            )

        try:
            meta = parse_torrent_bytes(file_bytes)
        except Exception as e:
            raise ValidationError(f"Invalid BitTorrent metadata format: {e}")

        ih = meta["info_hash"]
        dest_path = settings.torrent_metadata_path / f"{ih}.torrent"
        dest_path.write_bytes(file_bytes)

        files_list = [
            TorrentFileItem(
                index=f["index"],
                path=f["path"],
                size=f["size"],
                size_formatted=format_bytes(f["size"]),
                selected=True,
                priority="normal",
            )
            for f in meta["files"]
        ]

        t_meta = TorrentMetadataResponse(
            info_hash=ih,
            name=meta["name"],
            total_size=meta["total_size"],
            total_size_formatted=format_bytes(meta["total_size"]),
            file_count=len(files_list),
            piece_count=meta["piece_count"],
            piece_length=meta["piece_length"],
            trackers=meta["trackers"],
            created_date=meta["creation_date"],
            comment=meta["comment"],
            is_multi_file=meta["is_multi_file"],
            files=files_list,
            has_metadata=True,
        )

        MetadataCache.save(ih, {
            "info_hash": ih,
            "name": meta["name"],
            "total_size": meta["total_size"],
            "file_count": len(files_list),
            "files": meta["files"],
            "trackers": meta["trackers"],
            "has_metadata": True,
        })

        return str(dest_path), t_meta

    async def process_torrent_job(self, job: Job, t_cfg: Optional[TorrentDownloadConfig] = None) -> None:
        """
        Orchestrates full torrent job lifecycle (Section 2, 4, 34-37):
        QUEUED -> ACQUIRING_METADATA -> READY -> DOWNLOADING -> SEEDING -> COMPLETED
        or METADATA_FAILED if peers cannot be reached.
        Uses separate bounded concurrency for metadata discovery vs content downloading.
        """
        ih = job.info_hash
        if not ih and t_cfg:
            ih = t_cfg.info_hash
            job.info_hash = ih
        if not ih and MagnetParser.is_magnet_url(job.url):
            parsed = MagnetParser.parse_magnet(job.url)
            ih = parsed["info_hash"]
            job.info_hash = ih

        if not ih:
            raise ValidationError(f"Cannot identify BitTorrent info hash for job [{job.id}].")

        is_interactive = bool(
            job.interactive
            or (t_cfg and getattr(t_cfg, "interactive", False))
            or (t_cfg and getattr(t_cfg, "manual_review", False))
        )

        # 1. Check if metadata is already cached or local
        meta = MetadataCache.get(ih)
        has_metadata = bool(meta and meta.get("files"))

        if not has_metadata and self._engine:
            st = self.engine.get_status(ih)
            if st and st.has_metadata and st.files:
                has_metadata = True

        if not has_metadata and (job.url.startswith("file://") or job.url.endswith(".torrent")):
            has_metadata = True

        # Populate torrent_info if metadata is already present
        if has_metadata and not job.torrent_info:
            files_raw = []
            name = job.title or f"torrent_{ih[:8]}"
            tot_sz = 0
            if meta and meta.get("files"):
                files_raw = meta["files"]
                name = meta.get("name", name)
                tot_sz = meta.get("total_size", 0)
            elif self._engine:
                st = self.engine.get_status(ih)
                if st and st.files:
                    files_raw = st.files
                    name = st.name or name
                    tot_sz = st.total_size
            elif job.url.startswith("file://") or job.url.endswith(".torrent"):
                try:
                    fpath = Path(job.url.replace("file://", ""))
                    if fpath.exists():
                        parsed = parse_torrent_bytes(fpath.read_bytes())
                        files_raw = parsed.get("files", [])
                        name = parsed.get("name", name)
                        tot_sz = parsed.get("total_size", 0)
                except Exception:
                    pass

            if files_raw:
                files_list = [
                    TorrentFileItem(
                        index=f.get("index", idx),
                        path=f.get("path", f"file_{idx}"),
                        size=f.get("size", 0),
                        size_formatted=format_bytes(f.get("size", 0)),
                        selected=True,
                        priority="normal",
                    )
                    for idx, f in enumerate(files_raw)
                ]
                job.torrent_info = TorrentMetadataResponse(
                    info_hash=ih,
                    name=name,
                    total_size=tot_sz,
                    total_size_formatted=format_bytes(tot_sz),
                    file_count=len(files_list),
                    trackers=[],
                    is_multi_file=len(files_list) > 1,
                    files=files_list,
                    has_metadata=True,
                    magnet_uri=job.url if MagnetParser.is_magnet_url(job.url) else None,
                )
                if not job.title or job.title.startswith("magnet_") or job.title.startswith("torrent_"):
                    job.title = name
                if tot_sz > 0:
                    job.total_bytes = tot_sz

        # If metadata is already present and mode is interactive, pause payload and wait for selection
        if has_metadata and is_interactive:
            temp_dir = settings.temp_path / f"meta_{ih}"
            temp_dir.mkdir(parents=True, exist_ok=True)
            self.engine.add_torrent(
                torrent_spec=job.url,
                download_dir=temp_dir,
                dont_download=True,
            )
            num_files = len(job.torrent_info.files) if job.torrent_info else 0
            if num_files > 0:
                self.engine.set_file_priorities(ih, {i: "skip" for i in range(num_files)})
            job.status = JobStatus.WAITING_FOR_SELECTION
            job.current_stage = "Metadata ready: Select files to start download"
            JobRepository.save_job(job)
            job.emit_event()
            return

        # 2. Metadata Acquisition Phase (if needed)
        if not has_metadata:
            job.status = JobStatus.ACQUIRING_METADATA
            job.current_stage = "Waiting for torrent metadata..."
            job.started_at = time.time()
            JobRepository.save_job(job)
            job.emit_event()
            WebhookService.dispatch_event("torrent.metadata_started", {"job_id": job.id, "info_hash": ih})

            acquired = await self._acquire_metadata_loop(job, ih, t_cfg)
            if not acquired:
                # Metadata failed, status was set to METADATA_FAILED
                return

        # 3. If interactive mode (or manual review): wait for user file selection
        if is_interactive:
            job.status = JobStatus.WAITING_FOR_SELECTION
            job.current_stage = "Select files to start download"
            num_files = len(job.torrent_info.files) if job.torrent_info else 0
            if num_files > 0:
                self.engine.set_file_priorities(ih, {i: "skip" for i in range(num_files)})
            JobRepository.save_job(job)
            logger.info(f"TORRENT_SELECTION_READY job_id={job.id} info_hash={ih} files={num_files}")
            job.emit_event()
            return

        # 4. Content Download Phase (bounded by _download_semaphore)
        async with self._download_semaphore:
            if job.is_cancelled:
                return
            await self.start_job(job, t_cfg)

    async def _acquire_metadata_loop(self, job: Job, info_hash: str, t_cfg: Optional[TorrentDownloadConfig]) -> bool:
        """Performs bounded asynchronous metadata discovery with retry and backoff (Section 4, 14, 15, 35)."""
        async with self._metadata_semaphore:
            if job.is_cancelled:
                return False

            temp_dir = settings.temp_path / f"meta_{info_hash}"
            temp_dir.mkdir(parents=True, exist_ok=True)

            evt = self.engine.register_metadata_event(info_hash)
            now = time.time()
            if not job.torrent_created_at:
                job.torrent_created_at = now

            try:
                self.engine.add_torrent(
                    torrent_spec=job.url,
                    download_dir=temp_dir,
                    dont_download=True,
                )

                metadata_timeout = settings.TORRENT_METADATA_TIMEOUT
                loop = asyncio.get_running_loop()

                while job.retry_count <= job.max_retries:
                    if job.is_cancelled:
                        self.engine.remove(info_hash, delete_files=False)
                        return False

                    start_time = time.time()
                    while time.time() - start_time < metadata_timeout:
                        if job.is_cancelled:
                            self.engine.remove(info_hash, delete_files=False)
                            return False

                        # Event-driven wait: wakes up immediately when metadata arrives, or max 0.3s for telemetry
                        await loop.run_in_executor(None, lambda: evt.wait(timeout=0.3))
                        st = self.engine.get_status(info_hash)
                        if not st:
                            continue

                        # Track first peer discovery latency
                        if st.num_peers > 0 and not job.first_peer_at:
                            job.first_peer_at = time.time()

                        # Immediate check: if metadata and files are available, extract manifest without delay
                        if st.has_metadata and st.files:
                            now = time.time()
                            t_manifest_start = time.time()
                            job.metadata_received_at = now
                            job.file_tree_ready_at = now

                            logger.info(f"Metadata acquired for [{info_hash}] ({len(st.files)} files, {st.total_size} bytes)")
                            MetadataCache.save(info_hash, {
                                "info_hash": info_hash,
                                "name": st.name,
                                "total_size": st.total_size,
                                "file_count": len(st.files),
                                "files": st.files,
                                "magnet_uri": job.url,
                            })
                            if not job.title or job.title.startswith("magnet_") or job.title.startswith("torrent_"):
                                job.title = st.name
                            if st.total_size > 0:
                                job.total_bytes = st.total_size

                            # Construct structured torrent_info
                            files_list = [
                                TorrentFileItem(
                                    index=f.get("index", idx),
                                    path=f.get("path", f"file_{idx}"),
                                    size=f.get("size", 0),
                                    size_formatted=format_bytes(f.get("size", 0)),
                                    selected=True,
                                    priority="normal",
                                )
                                for idx, f in enumerate(st.files)
                            ]
                            job.torrent_info = TorrentMetadataResponse(
                                info_hash=info_hash,
                                name=st.name,
                                total_size=st.total_size,
                                total_size_formatted=format_bytes(st.total_size),
                                file_count=len(files_list),
                                trackers=[],
                                is_multi_file=len(files_list) > 1,
                                files=files_list,
                                has_metadata=True,
                                magnet_uri=job.url,
                            )

                            manifest_ms = (time.time() - t_manifest_start) * 1000
                            logger.info(
                                f"TORRENT_MANIFEST_READY info_hash={info_hash} "
                                f"file_count={len(files_list)} duration_ms={manifest_ms:.2f}"
                            )

                            ref_start = job.magnet_received_at or job.job_created_at or start_time
                            meta_ms = (job.metadata_received_at - ref_start) * 1000
                            peer_ms = ((job.first_peer_at - ref_start) * 1000) if job.first_peer_at else None
                            logger.info(
                                f"torrent_lifecycle_metric info_hash={info_hash} job_id={job.id} "
                                f"metadata_latency_ms={meta_ms:.1f} first_peer_latency_ms={peer_ms or 0:.1f} "
                                f"peers={st.num_peers} trackers={st.trackers_contacted} files={len(files_list)}"
                            )

                            job.torrent_telemetry = TorrentTelemetry(
                                info_hash=info_hash,
                                name=st.name,
                                state=map_torrent_state(st),
                                total_size=st.total_size,
                                total_size_formatted=format_bytes(st.total_size),
                                downloaded_bytes=st.total_downloaded,
                                uploaded_bytes=st.total_uploaded,
                                download_speed=f"{format_bytes(st.download_rate)}/s",
                                upload_speed=f"{format_bytes(st.upload_rate)}/s",
                                ratio=st.ratio,
                                peers=st.num_peers,
                                seeds=st.num_seeds,
                                leeches=st.num_leeches,
                                seeding_mode="stop",
                                is_seeding=False,
                                file_count=len(st.files),
                                files=st.files,
                                trackers_contacted=st.trackers_contacted,
                                dht_active=st.dht_active,
                                metadata_phase="Metadata received",
                                metadata_retry_count=job.retry_count,
                                cached=False,
                            )
                            job.current_stage = "Metadata received · Preparing file selection..."
                            JobRepository.save_job(job)
                            job.emit_event()

                            WebhookService.dispatch_event(
                                "torrent.metadata_ready",
                                {"job_id": job.id, "info_hash": info_hash, "name": st.name, "files_count": len(st.files), "total_size": st.total_size},
                            )
                            return True

                        # While metadata is NOT yet available, emit discovery telemetry
                        phase = st.metadata_phase or ("Contacting trackers" if st.num_peers == 0 else f"{st.num_peers} peers discovered")
                        job.current_stage = f"Acquiring torrent metadata... ({phase})"
                        job.torrent_telemetry = TorrentTelemetry(
                            info_hash=info_hash,
                            name=st.name,
                            state=map_torrent_state(st),
                            total_size=st.total_size,
                            total_size_formatted=format_bytes(st.total_size),
                            downloaded_bytes=st.total_downloaded,
                            uploaded_bytes=st.total_uploaded,
                            download_speed=f"{format_bytes(st.download_rate)}/s",
                            upload_speed=f"{format_bytes(st.upload_rate)}/s",
                            ratio=st.ratio,
                            peers=st.num_peers,
                            seeds=st.num_seeds,
                            leeches=st.num_leeches,
                            seeding_mode="stop",
                            is_seeding=False,
                            file_count=len(st.files),
                            files=st.files,
                            trackers_contacted=st.trackers_contacted,
                            dht_active=st.dht_active,
                            metadata_phase=phase,
                            metadata_retry_count=job.retry_count,
                            cached=False,
                        )
                        JobRepository.save_job(job)
                        job.emit_event()

                    # Timeout on current attempt
                    if job.retry_count < job.max_retries:
                        job.retry_count += 1
                        backoff = min(120, 15 * (2 ** (job.retry_count - 1)))
                        job.next_retry_at = time.time() + backoff
                        job.current_stage = f"Retrieving metadata — Attempt {job.retry_count} of {job.max_retries} — Next retry in {int(backoff)}s"
                        JobRepository.save_job(job)
                        job.emit_event()
                        WebhookService.dispatch_event(
                            "torrent.metadata_progress",
                            {"job_id": job.id, "info_hash": info_hash, "retry_count": job.retry_count, "next_retry_in": int(backoff)},
                        )
                        await asyncio.sleep(backoff)
                    else:
                        job.status = JobStatus.METADATA_FAILED
                        job.error_message = "Could not retrieve torrent metadata. The torrent may currently have no reachable peers. You can keep this job queued and ashoriN will retry automatically."
                        job.current_stage = "Metadata acquisition timed out"
                        job.completed_at = time.time()
                        JobRepository.save_job(job)
                        job.emit_event()
                        WebhookService.dispatch_event(
                            "torrent.metadata_failed",
                            {"job_id": job.id, "info_hash": info_hash, "error": job.error_message},
                        )
                        return False
            finally:
                self.engine.unregister_metadata_event(info_hash)
        return False

    async def start_job(self, job: Job, t_cfg: Optional[TorrentDownloadConfig] = None) -> None:
        """Starts background download of a torrent job and monitors its progress."""
        job.download_started_at = time.time()
        ih = job.info_hash
        if not ih and t_cfg:
            ih = t_cfg.info_hash
            job.info_hash = ih

        if not ih:
            # Parse from job.url
            if MagnetParser.is_magnet_url(job.url):
                parsed = MagnetParser.parse_magnet(job.url)
                ih = parsed["info_hash"]
                job.info_hash = ih

        if not ih:
            raise ValidationError(f"Cannot identify BitTorrent info hash for job [{job.id}].")

        safe_name = FileService.sanitize_filename(job.title or f"torrent_{ih[:8]}")
        is_multi = t_cfg and t_cfg.selected_indices and len(t_cfg.selected_indices) > 1

        # Destination resolution
        torrent_base = settings.torrent_storage_path if hasattr(settings, "torrent_storage_path") and settings.torrent_storage_path else settings.download_path
        if t_cfg and t_cfg.destination_folder:
            dest_dir = FileService.get_safe_file_path(torrent_base, t_cfg.destination_folder)
        elif is_multi:
            dest_dir = torrent_base / safe_name
        else:
            dest_dir = torrent_base / safe_name

        # Storage Preflight (Section 14 & 15)
        # Real write probe, permission verification, read-only detection, disk usage for actual destination
        from app.services.storage_service import StorageService
        required_size = job.total_bytes or 0
        dest_dir = StorageService.validate_destination_for_download(
            dest_dir=dest_dir,
            required_bytes=required_size,
            create_if_missing=True,
        )
        job.output_path = dest_dir

        seeding_mode = t_cfg.seeding_mode if t_cfg else "stop"
        selected_indices = (t_cfg.selected_indices if t_cfg.selected_indices is not None else t_cfg.selected_files) if t_cfg else None
        file_priorities = t_cfg.file_priorities if t_cfg else None

        # Determine torrent spec
        torrent_spec = None
        torrent_file_path = t_cfg.torrent_file_path if t_cfg else None
        if torrent_file_path and Path(torrent_file_path).exists():
            torrent_spec = str(Path(torrent_file_path).resolve())
        elif (settings.torrent_metadata_path / f"{ih}.torrent").exists():
            torrent_spec = str((settings.torrent_metadata_path / f"{ih}.torrent").resolve())
        elif t_cfg and t_cfg.magnet_uri:
            torrent_spec = t_cfg.magnet_uri
        elif MagnetParser.is_magnet_url(job.url):
            torrent_spec = job.url

        if not torrent_spec:
            raise ValidationError(f"No valid torrent spec or magnet URI found for job [{job.id}].")

        # Save initial torrent record
        tor_id = str(uuid.uuid4())
        job.torrent_id = tor_id
        TorrentRepository.save_torrent({
            "id": tor_id,
            "job_id": job.id,
            "info_hash": ih,
            "name": safe_name,
            "magnet_uri": job.url if MagnetParser.is_magnet_url(job.url) else None,
            "torrent_file_path": torrent_spec if torrent_spec.endswith(".torrent") else None,
            "total_size": job.total_bytes or 0,
            "status": "DOWNLOADING",
            "seeding_mode": seeding_mode,
            "download_dir": str(dest_dir.resolve()),
        })

        # Add to engine with active piece downloading
        self.engine.add_torrent(
            torrent_spec=torrent_spec,
            download_dir=dest_dir,
            selected_indices=selected_indices,
            file_priorities=file_priorities,
            dont_download=False,
        )

        initial_status = self.engine.get_status(ih)
        if initial_status and (not initial_status.has_metadata or map_torrent_state(initial_status) == "metadata"):
            job.status = JobStatus.ACQUIRING_METADATA
            job.current_stage = "Waiting for torrent metadata..."
        else:
            job.status = JobStatus.DOWNLOADING
            job.current_stage = "Downloading torrent pieces"

        JobRepository.save_job(job)
        job.emit_event()
        WebhookService.dispatch_event("torrent.started", {"job_id": job.id, "info_hash": ih, "name": safe_name})

        # Start background polling loop
        task = asyncio.create_task(self._poll_torrent(job, tor_id, ih, dest_dir, seeding_mode))
        async with self._lock:
            self._active_tasks[job.id] = task

    async def _poll_torrent(
        self,
        job: Job,
        torrent_id: str,
        info_hash: str,
        download_dir: Path,
        seeding_mode: str,
    ) -> None:
        """Monitors download progress, updates telemetry, handles seeding, and catalogs media."""
        start_seeding_time: Optional[float] = None
        metadata_start_time = time.time()

        try:
            while True:
                await asyncio.sleep(1.0)
                if job.is_cancelled:
                    self.engine.remove(info_hash, delete_files=False)
                    break

                status = self.engine.get_status(info_hash)
                if not status:
                    break

                # Check for engine or download errors
                if status.error_message or status.state == "error":
                    err_msg = status.error_message or "Torrent error encountered"
                    mapped = map_torrent_error(err_msg)
                    logger.error(f"Torrent engine error for [{info_hash}]: {mapped} ({err_msg})")
                    from app.services.job_manager import job_manager
                    await job_manager._handle_job_failure(job, f"{mapped}: {err_msg}")
                    break

                # Handle metadata acquisition state and timeout
                norm_state = map_torrent_state(status)
                if not status.has_metadata or norm_state == "metadata":
                    if job.status not in (JobStatus.WAITING_FOR_METADATA, JobStatus.ACQUIRING_METADATA):
                        job.status = JobStatus.ACQUIRING_METADATA
                        job.current_stage = "Waiting for torrent metadata..."
                        JobRepository.save_job(job)
                        job.emit_event()

                    if (time.time() - metadata_start_time) > settings.TORRENT_METADATA_TIMEOUT:
                        logger.warning(
                            "torrent_metadata_timeout",
                            extra={"info_hash": info_hash, "timeout": settings.TORRENT_METADATA_TIMEOUT},
                        )
                        self.engine.remove(info_hash, delete_files=False)
                        from app.services.job_manager import job_manager
                        await job_manager._handle_job_failure(
                            job,
                            "Couldn't retrieve torrent metadata. The torrent may be offline or its trackers may be unavailable.",
                        )
                        break
                else:
                    # Metadata acquired: if previously waiting for metadata, transition to DOWNLOADING
                    if job.status in (JobStatus.WAITING_FOR_METADATA, JobStatus.ACQUIRING_METADATA):
                        job.status = JobStatus.DOWNLOADING
                        job.current_stage = "Downloading torrent pieces"
                        if status.total_size > 0:
                            job.total_bytes = status.total_size
                        if not job.title or job.title.startswith("magnet_") or job.title.startswith("torrent_"):
                            job.title = status.name
                        MetadataCache.save(info_hash, {
                            "info_hash": info_hash,
                            "name": status.name,
                            "total_size": status.total_size,
                            "file_count": len(status.files),
                            "files": status.files,
                            "magnet_uri": job.url,
                        })
                        JobRepository.save_job(job)
                        job.emit_event()

                # Update job telemetry
                job.progress = status.progress * 100.0
                job.speed = f"{format_bytes(status.download_rate)}/s" if status.download_rate > 0 else None
                job.downloaded_bytes = status.total_downloaded
                if status.total_size > 0:
                    job.total_bytes = status.total_size

                # ETA calculation
                if status.download_rate > 0 and status.total_size > status.total_downloaded:
                    rem_bytes = status.total_size - status.total_downloaded
                    rem_sec = int(rem_bytes / status.download_rate)
                    mins, secs = divmod(rem_sec, 60)
                    hrs, mins = divmod(mins, 60)
                    job.eta = f"{hrs:02d}:{mins:02d}:{secs:02d}" if hrs > 0 else f"{mins:02d}:{secs:02d}"
                else:
                    job.eta = None

                # Build TorrentTelemetry snapshot
                telemetry = TorrentTelemetry(
                    info_hash=info_hash,
                    name=status.name,
                    state=norm_state,
                    total_size=status.total_size,
                    total_size_formatted=format_bytes(status.total_size),
                    downloaded_bytes=status.total_downloaded,
                    uploaded_bytes=status.total_uploaded,
                    download_speed=f"{format_bytes(status.download_rate)}/s",
                    upload_speed=f"{format_bytes(status.upload_rate)}/s",
                    ratio=status.ratio,
                    peers=status.num_peers,
                    seeds=status.num_seeds,
                    leeches=status.num_leeches,
                    eta=job.eta,
                    seeding_mode=seeding_mode,
                    is_seeding=status.is_seeding,
                    file_count=len(status.files),
                    files=status.files,
                    trackers_contacted=status.trackers_contacted,
                    dht_active=status.dht_active,
                    metadata_phase=status.metadata_phase,
                    metadata_retry_count=job.retry_count,
                    cached=False,
                )
                job.torrent_telemetry = telemetry

                # Update Torrent in SQLite
                TorrentRepository.save_torrent({
                    "id": torrent_id,
                    "job_id": job.id,
                    "info_hash": info_hash,
                    "name": status.name,
                    "total_size": status.total_size,
                    "downloaded_size": status.total_downloaded,
                    "uploaded_size": status.total_uploaded,
                    "ratio": status.ratio,
                    "status": "SEEDING" if (status.is_seeding or norm_state == "seeding") else ("COMPLETED" if (status.is_finished or norm_state == "finished") else "DOWNLOADING"),
                    "seeding_mode": seeding_mode,
                    "download_dir": str(download_dir.resolve()),
                })

                # Check completion / seeding transition
                if status.is_finished or status.progress >= 1.0 or norm_state in ("finished", "seeding"):
                    self._finalize_torrent_job_output(job, download_dir)
                    if status.is_seeding or norm_state == "seeding" or seeding_mode != "stop":
                        if job.status != JobStatus.SEEDING:
                            job.status = JobStatus.SEEDING
                            job.current_stage = "Seeding torrent pieces"
                            start_seeding_time = time.time()
                            JobRepository.save_job(job)
                            job.emit_event()
                            WebhookService.dispatch_event("torrent.seeding_started", {"job_id": job.id, "info_hash": info_hash})

                        # Check seeding termination condition
                        should_stop_seeding = False
                        if seeding_mode == "stop":
                            should_stop_seeding = True
                        elif seeding_mode == "ratio_1" and status.ratio >= 1.0:
                            should_stop_seeding = True
                        elif seeding_mode == "ratio_2" and status.ratio >= 2.0:
                            should_stop_seeding = True
                        elif seeding_mode == "time_30m" and start_seeding_time and (time.time() - start_seeding_time >= 1800):
                            should_stop_seeding = True
                        elif seeding_mode == "time_2h" and start_seeding_time and (time.time() - start_seeding_time >= 7200):
                            should_stop_seeding = True

                        if should_stop_seeding:
                            logger.info(f"Seeding policy ({seeding_mode}) fulfilled for [{info_hash}]. Stopping seeding.")
                            self.engine.pause(info_hash)
                            job.status = JobStatus.COMPLETED
                            job.current_stage = "Completed"
                            job.completed_at = time.time()
                            JobRepository.save_job(job)
                            job.emit_event()
                            WebhookService.dispatch_event("torrent.seeding_stopped", {"job_id": job.id, "info_hash": info_hash})
                            break
                    else:
                        # Not seeding or mode is stop
                        job.status = JobStatus.COMPLETED
                        job.current_stage = "Completed"
                        job.completed_at = time.time()
                        JobRepository.save_job(job)
                        job.emit_event()
                        WebhookService.dispatch_event("torrent.completed", {"job_id": job.id, "info_hash": info_hash})
                        break

                JobRepository.save_job(job)
                job.emit_event()

            # Download complete: index media files into Media Library
            if job.status in (JobStatus.COMPLETED, JobStatus.SEEDING):
                self._finalize_torrent_job_output(job, download_dir)
                await self._index_torrent_media(job, torrent_id, download_dir)
                try:
                    from app.services.media.import_service import ImportService
                    asyncio.create_task(ImportService.inspect_job_background(job.id))
                except Exception as e:
                    logger.debug(f"Could not trigger background import inspection for torrent [{job.id}]: {e}")
        finally:
            async with self._lock:
                self._active_tasks.pop(job.id, None)

    def _finalize_torrent_job_output(self, job: Job, download_dir: Path) -> None:
        """
        Inspects completed download directory to set output_path, output_filename, output_type, and file_count.
        Ensures files in temporary or alternate locations are relocated, resolves the actual content root,
        and accounts for multi-file folder hierarchies.
        """
        ih = job.info_hash or ""
        meta_temp_dir = settings.temp_path / f"meta_{ih}" if ih else None

        # Relocation fallback: if download_dir has no payload files but meta_temp_dir does, relocate them
        if download_dir.exists() and meta_temp_dir and meta_temp_dir.exists():
            dest_files = [f for f in download_dir.rglob("*") if f.is_file() and not f.name.endswith((".part", ".ytdl", ".temp", ".tmp", ".zip"))]
            temp_files = [f for f in meta_temp_dir.rglob("*") if f.is_file() and not f.name.endswith((".part", ".ytdl", ".temp", ".tmp", ".zip"))]
            if not dest_files and temp_files:
                logger.info(f"Relocating {len(temp_files)} torrent payload files from temp {meta_temp_dir} to {download_dir}")
                for item in meta_temp_dir.iterdir():
                    if item.name.startswith("."):
                        continue
                    target = download_dir / item.name
                    if not target.exists():
                        try:
                            shutil.move(str(item), str(target))
                        except Exception as e:
                            logger.warning(f"Error moving {item} to {target}: {e}")

        if not download_dir.exists():
            logger.warning(f"download_dir {download_dir} does not exist during finalization for job [{job.id}]")
            return

        valid_files: List[Path] = []
        total_size = 0
        try:
            for p in download_dir.rglob("*"):
                if not p.is_file():
                    continue
                if p.name.endswith((".part", ".ytdl", ".temp", ".torrent", ".tmp", ".zip")):
                    continue
                # Symlink safety check
                try:
                    resolved = p.resolve()
                    if not resolved.is_relative_to(download_dir.resolve()):
                        logger.warning(f"Skipping symlink escaping download dir: {p} -> {resolved}")
                        continue
                except Exception:
                    continue
                valid_files.append(p)
                try:
                    total_size += p.stat().st_size
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Error scanning download_dir {download_dir} for output finalization: {e}")

        job.output_filesize = total_size or job.total_bytes

        if len(valid_files) == 1:
            single_file = valid_files[0]
            job.output_path = single_file
            job.output_filename = single_file.name
            job.output_type = "file"
            job.file_count = 1
        elif len(valid_files) > 1:
            # Multi-file torrent: determine the actual content root
            content_root = download_dir
            # Check if download_dir contains exactly one child directory containing all valid files
            direct_children = [c for c in download_dir.iterdir() if not c.name.startswith(".")]
            if len(direct_children) == 1 and direct_children[0].is_dir():
                child_dir = direct_children[0]
                child_files = [f for f in child_dir.rglob("*") if f.is_file() and not f.name.endswith((".part", ".ytdl", ".temp", ".tmp", ".zip"))]
                if len(child_files) == len(valid_files):
                    content_root = child_dir

            job.output_path = content_root
            archive_stem = FileService.sanitize_filename(content_root.name or job.title or "torrent")
            job.output_filename = f"{archive_stem}.zip"
            job.output_type = "directory"
            job.file_count = len(valid_files)
        else:
            job.output_path = download_dir
            job.output_type = "directory"
            job.file_count = 0

        JobRepository.save_job(job)
        job.emit_event()

    async def _index_torrent_media(self, job: Job, torrent_id: str, download_dir: Path) -> None:
        """Scans downloaded directory and catalogs supported audio/video files into the Media Library."""
        if not download_dir.exists():
            return

        cataloged = 0
        try:
            for root, _, files in os.walk(download_dir):
                for f in files:
                    p = Path(root) / f
                    ext = p.suffix.lower()
                    if ext in MEDIA_EXTENSIONS:
                        torrent_base = settings.torrent_storage_path if hasattr(settings, "torrent_storage_path") and settings.torrent_storage_path else settings.download_path
                        try:
                            rel_path = str(p.relative_to(torrent_base))
                        except ValueError:
                            try:
                                rel_path = str(p.relative_to(settings.download_path))
                            except ValueError:
                                rel_path = p.name
                        sz = p.stat().st_size
                        title = p.stem

                        # Check if already in media library
                        try:
                            existing = MediaRepository.find_by_relative_path(rel_path)
                            if not existing:
                                is_audio = ext in {".mp3", ".flac", ".m4a", ".wav", ".ogg", ".opus"}
                                item_id = str(uuid.uuid4())
                                now = time.time()
                                MediaRepository.save_media_item({
                                    "id": item_id,
                                    "job_id": job.id,
                                    "title": title,
                                    "filename": p.name,
                                    "relative_path": rel_path,
                                    "source_url": job.url,
                                    "extractor": "torrent",
                                    "media_id": f"tor_{job.info_hash}_{p.name}",
                                    "uploader": job.title or "Torrent",
                                    "playlist_name": job.title or "Torrent Collection",
                                    "container": ext.lstrip("."),
                                    "filesize": sz,
                                    "is_favorite": 0,
                                    "is_protected": 0,
                                    "source_provider": "torrent",
                                    "torrent_id": torrent_id,
                                    "created_at": now,
                                    "downloaded_at": now,
                                })
                                cataloged += 1
                        except Exception as e:
                            logger.warning(f"Failed to catalog torrent media file {p}: {e}")
            if cataloged > 0:
                logger.info(f"Indexed {cataloged} media item(s) from torrent [{job.info_hash}] into Media Library.")
        except Exception as e:
            logger.error(f"Error indexing media for torrent [{job.id}]: {e}")

    async def pause_torrent(self, job_id: str) -> Job:
        job = JobRepository.get_job(job_id)
        if not job:
            raise ValidationError(f"Job {job_id} not found.")
        ih = job.info_hash
        if ih:
            self.engine.pause(ih)
            job.status = JobStatus.PAUSED
            job.current_stage = "Paused"
            JobRepository.save_job(job)
            job.emit_event()
            if job.torrent_id:
                TorrentRepository.save_torrent({
                    "id": job.torrent_id,
                    "info_hash": ih,
                    "name": job.title or "Torrent",
                    "status": "PAUSED",
                })
        return job

    async def resume_torrent(self, job_id: str) -> Job:
        job = JobRepository.get_job(job_id)
        if not job:
            raise ValidationError(f"Job {job_id} not found.")
        ih = job.info_hash
        if ih:
            self.engine.resume(ih)
            job.status = JobStatus.DOWNLOADING
            job.current_stage = "Downloading torrent pieces"
            JobRepository.save_job(job)
            job.emit_event()
            if job.torrent_id:
                TorrentRepository.save_torrent({
                    "id": job.torrent_id,
                    "info_hash": ih,
                    "name": job.title or "Torrent",
                    "status": "DOWNLOADING",
                })
        return job

    async def force_recheck(self, job_id: str) -> Job:
        job = JobRepository.get_job(job_id)
        if not job:
            raise ValidationError(f"Job {job_id} not found.")
        ih = job.info_hash
        if ih:
            self.engine.force_recheck(ih)
            job.current_stage = "Checking piece hashes"
            JobRepository.save_job(job)
            job.emit_event()
        return job

    async def stop_seeding(self, job_id: str) -> Job:
        job = JobRepository.get_job(job_id)
        if not job:
            raise ValidationError(f"Job {job_id} not found.")
        ih = job.info_hash
        if ih:
            self.engine.pause(ih)
            job.status = JobStatus.COMPLETED
            job.current_stage = "Completed (seeding stopped)"
            if job.output_path and job.output_path.exists():
                scan_dir = job.output_path if job.output_path.is_dir() else job.output_path.parent
                self._finalize_torrent_job_output(job, scan_dir)
            JobRepository.save_job(job)
            job.emit_event()
            WebhookService.dispatch_event("torrent.seeding_stopped", {"job_id": job.id, "info_hash": ih})
        return job

    async def remove_torrent(self, job_id: str, delete_files: bool = False) -> None:
        job = JobRepository.get_job(job_id)
        ih = job.info_hash if job else None
        if ih:
            self.engine.remove(ih, delete_files=delete_files)
        if job and job.torrent_id:
            TorrentRepository.delete_torrent(job.torrent_id)


# Global singleton
torrent_service = TorrentService()
