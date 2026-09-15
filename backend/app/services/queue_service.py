import asyncio
import time
from typing import List, Optional
from app.db.database import get_db
from app.models.schemas import JobStatus
from app.repositories.job_repository import JobRepository
from app.utils.logger import logger


class QueueService:
    @staticmethod
    def get_priority_weight(priority: str) -> int:
        p = str(priority).upper()
        if p == "HIGH":
            return 1
        elif p == "NORMAL":
            return 2
        elif p == "LOW":
            return 3
        return 2

    @staticmethod
    def reorder_queue(job_ids: List[str]) -> bool:
        """Updates queue_order index for a list of job IDs."""
        with get_db() as conn:
            cursor = conn.cursor()
            for idx, jid in enumerate(job_ids):
                cursor.execute("UPDATE jobs SET queue_order = ? WHERE id = ?", (idx, jid))
        return True

    @staticmethod
    def set_job_priority(job_id: str, priority: str) -> bool:
        """Sets the priority of a job (HIGH, NORMAL, LOW)."""
        valid_p = priority.upper() if priority.upper() in ("HIGH", "NORMAL", "LOW") else "NORMAL"
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE jobs SET priority = ? WHERE id = ?", (valid_p, job_id))
            return cursor.rowcount > 0

    @staticmethod
    def schedule_job(job_id: str, scheduled_for: float, schedule_type: str = "once") -> bool:
        """Schedules a job for future execution."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE jobs SET scheduled_for = ?, schedule_type = ?, status = 'QUEUED', current_stage = 'Scheduled' WHERE id = ?",
                (scheduled_for, schedule_type, job_id),
            )
            return cursor.rowcount > 0

    @staticmethod
    def recover_interrupted_jobs() -> int:
        """
        On container startup, marks any jobs left in active execution states as
        interrupted so they don't remain stuck indefinitely.
        """
        now = time.time()
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE jobs
                SET status = 'FAILED',
                    current_stage = 'Interrupted by server restart',
                    error_message = 'Job was interrupted by a container or server restart.',
                    completed_at = ?
                WHERE status IN ('DOWNLOADING', 'PROCESSING', 'ANALYZING')
                """,
                (now,),
            )
            count = cursor.rowcount
            if count > 0:
                logger.warning(f"Recovered {count} interrupted jobs from previous container session.")
            return count
