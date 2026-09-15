import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.db.database import get_db
from app.models.job import Job
from app.models.schemas import DownloadConfig, JobStatus
from app.utils.logger import logger


class JobRepository:
    @staticmethod
    def save_job(job: Job) -> None:
        """Persists or updates job in SQLite database."""
        cfg_json = None
        if job.config:
            if hasattr(job.config, "model_dump"):
                cfg_json = json.dumps(job.config.model_dump())
            elif isinstance(job.config, dict):
                cfg_json = json.dumps(job.config)

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO jobs (
                    id, url, title, thumbnail, status, priority, queue_order,
                    progress, speed, eta, current_stage, downloaded_bytes, total_bytes,
                    retry_count, max_retries, next_retry_at, scheduled_for, schedule_type,
                    bandwidth_limit, config_json, profile_id, output_filename, output_path,
                    output_filesize, error_message, is_playlist, playlist_title,
                    total_items, completed_items, failed_items, skipped_items,
                    current_item_index, current_item_title, created_at, started_at, completed_at,
                    provider, input_type, info_hash, movie_id, episode_id,
                    job_type, is_upgrade, previous_quality, upgrade_reason
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                ON CONFLICT(id) DO UPDATE SET
                    status=excluded.status,
                    priority=excluded.priority,
                    queue_order=excluded.queue_order,
                    progress=excluded.progress,
                    speed=excluded.speed,
                    eta=excluded.eta,
                    current_stage=excluded.current_stage,
                    downloaded_bytes=excluded.downloaded_bytes,
                    total_bytes=excluded.total_bytes,
                    retry_count=excluded.retry_count,
                    next_retry_at=excluded.next_retry_at,
                    scheduled_for=excluded.scheduled_for,
                    bandwidth_limit=excluded.bandwidth_limit,
                    config_json=coalesce(excluded.config_json, jobs.config_json),
                    output_filename=excluded.output_filename,
                    output_path=excluded.output_path,
                    output_filesize=excluded.output_filesize,
                    error_message=excluded.error_message,
                    completed_items=excluded.completed_items,
                    failed_items=excluded.failed_items,
                    skipped_items=excluded.skipped_items,
                    current_item_index=excluded.current_item_index,
                    current_item_title=excluded.current_item_title,
                    started_at=excluded.started_at,
                    completed_at=excluded.completed_at,
                    provider=excluded.provider,
                    input_type=excluded.input_type,
                    info_hash=coalesce(excluded.info_hash, jobs.info_hash),
                    movie_id=coalesce(excluded.movie_id, jobs.movie_id),
                    episode_id=coalesce(excluded.episode_id, jobs.episode_id),
                    job_type=coalesce(excluded.job_type, jobs.job_type),
                    is_upgrade=coalesce(excluded.is_upgrade, jobs.is_upgrade),
                    previous_quality=coalesce(excluded.previous_quality, jobs.previous_quality),
                    upgrade_reason=coalesce(excluded.upgrade_reason, jobs.upgrade_reason)
                """,
                (
                    job.id,
                    job.url,
                    job.title,
                    job.thumbnail,
                    job.status.value if isinstance(job.status, JobStatus) else str(job.status),
                    getattr(job, "priority", "NORMAL"),
                    getattr(job, "queue_order", 0),
                    round(job.progress, 1),
                    job.speed,
                    job.eta,
                    job.current_stage,
                    job.downloaded_bytes,
                    job.total_bytes,
                    getattr(job, "retry_count", 0),
                    getattr(job, "max_retries", 3),
                    getattr(job, "next_retry_at", None),
                    getattr(job, "scheduled_for", None),
                    getattr(job, "schedule_type", "once"),
                    getattr(job, "bandwidth_limit", 0),
                    cfg_json,
                    getattr(job, "profile_id", "recommended"),
                    job.output_filename,
                    str(job.output_path) if job.output_path else None,
                    job.output_filesize,
                    job.error_message,
                    1 if job.is_playlist else 0,
                    job.playlist_title,
                    job.total_items,
                    job.completed_items,
                    job.failed_items,
                    job.skipped_items,
                    job.current_item_index,
                    job.current_item_title,
                    job.created_at,
                    job.started_at,
                    job.completed_at,
                    getattr(job, "provider", "ytdlp"),
                    getattr(job, "input_type", "url"),
                    getattr(job, "info_hash", None),
                    getattr(job, "movie_id", None),
                    getattr(job, "episode_id", None),
                    getattr(job, "job_type", "NORMAL"),
                    1 if getattr(job, "is_upgrade", False) else 0,
                    getattr(job, "previous_quality", None),
                    getattr(job, "upgrade_reason", None),
                ),
            )

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> Job:
        """Converts SQLite Row to Job model."""
        cfg = None
        if row["config_json"]:
            try:
                data = json.loads(row["config_json"])
                cfg = DownloadConfig(**data)
            except Exception:
                cfg = None

        job = Job(
            id=row["id"],
            url=row["url"],
            title=row["title"],
            thumbnail=row["thumbnail"],
            status=JobStatus(row["status"]) if row["status"] in JobStatus._value2member_map_ else JobStatus.FAILED,
            progress=row["progress"] or 0.0,
            speed=row["speed"],
            eta=row["eta"],
            current_stage=row["current_stage"] or "Queued",
            downloaded_bytes=row["downloaded_bytes"] or 0,
            total_bytes=row["total_bytes"],
            created_at=row["created_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            output_filename=row["output_filename"],
            output_filesize=row["output_filesize"],
            output_path=Path(row["output_path"]) if row["output_path"] else None,
            error_message=row["error_message"],
            config=cfg,
            is_playlist=bool(row["is_playlist"]),
            playlist_title=row["playlist_title"],
            total_items=row["total_items"] or 0,
            completed_items=row["completed_items"] or 0,
            failed_items=row["failed_items"] or 0,
            skipped_items=row["skipped_items"] or 0,
            current_item_index=row["current_item_index"] or 0,
            current_item_title=row["current_item_title"],
        )
        job.priority = row["priority"] or "NORMAL"
        job.queue_order = row["queue_order"] or 0
        job.retry_count = row["retry_count"] or 0
        job.max_retries = row["max_retries"] or 3
        job.next_retry_at = row["next_retry_at"]
        job.scheduled_for = row["scheduled_for"]
        job.schedule_type = row["schedule_type"] or "once"
        job.bandwidth_limit = row["bandwidth_limit"] or 0
        job.profile_id = row["profile_id"] or "recommended"
        row_keys = row.keys()
        if "provider" in row_keys and row["provider"]:
            job.provider = row["provider"]
        if "input_type" in row_keys and row["input_type"]:
            job.input_type = row["input_type"]
        if "info_hash" in row_keys and row["info_hash"]:
            job.info_hash = row["info_hash"]
        if "movie_id" in row_keys and row["movie_id"]:
            job.movie_id = row["movie_id"]
        if "episode_id" in row_keys and row["episode_id"]:
            job.episode_id = row["episode_id"]
        if "job_type" in row_keys and row["job_type"]:
            job.job_type = row["job_type"]
        if "is_upgrade" in row_keys and row["is_upgrade"] is not None:
            job.is_upgrade = bool(row["is_upgrade"])
        if "previous_quality" in row_keys and row["previous_quality"]:
            job.previous_quality = row["previous_quality"]
        if "upgrade_reason" in row_keys and row["upgrade_reason"]:
            job.upgrade_reason = row["upgrade_reason"]
        return job

    @staticmethod
    def get_job(job_id: str) -> Optional[Job]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return JobRepository._row_to_job(row)

    @staticmethod
    def list_jobs(limit: int = 100, offset: int = 0) -> List[Job]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM jobs
                ORDER BY
                    CASE priority
                        WHEN 'HIGH' THEN 1
                        WHEN 'NORMAL' THEN 2
                        WHEN 'LOW' THEN 3
                        ELSE 2
                    END ASC,
                    queue_order ASC,
                    created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
            return [JobRepository._row_to_job(r) for r in cursor.fetchall()]

    @staticmethod
    def delete_job(job_id: str) -> None:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))

    @staticmethod
    def recover_interrupted_jobs() -> int:
        """Sets DOWNLOADING or PROCESSING jobs to INTERRUPTED on container restart."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE jobs
                SET status = 'INTERRUPTED', current_stage = 'Interrupted by server restart'
                WHERE status IN ('DOWNLOADING', 'PROCESSING')
                """
            )
            count = cursor.rowcount
            if count > 0:
                logger.info(f"Marked {count} active jobs as INTERRUPTED after restart.")
            return count

    @staticmethod
    def get_next_runnable_job() -> Optional[Job]:
        """
        Picks the highest priority eligible job:
        - QUEUED
        - SCHEDULED where scheduled_for <= now
        - RETRY_WAIT where next_retry_at <= now
        """
        now = time.time()
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM jobs
                WHERE status = 'QUEUED'
                   OR (status = 'SCHEDULED' AND scheduled_for <= ?)
                   OR (status = 'RETRY_WAIT' AND next_retry_at <= ?)
                ORDER BY
                    CASE priority
                        WHEN 'HIGH' THEN 1
                        WHEN 'NORMAL' THEN 2
                        WHEN 'LOW' THEN 3
                        ELSE 2
                    END ASC,
                    queue_order ASC,
                    created_at ASC
                LIMIT 1
                """,
                (now, now),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return JobRepository._row_to_job(row)
