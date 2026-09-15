import datetime
import time
from fastapi import APIRouter
from app.db.database import get_db
from app.models.schemas import StatisticsResponse
from app.services.file_service import FileService

router = APIRouter(prefix="/api/statistics", tags=["Statistics"])


@router.get("", response_model=StatisticsResponse)
async def get_statistics():
    """Returns aggregated system analytics and download metrics."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Overall job totals
        cursor.execute("SELECT COUNT(*) FROM jobs")
        total_downloads = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM jobs WHERE status = 'COMPLETED'")
        completed_downloads = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM jobs WHERE status = 'FAILED'")
        failed_downloads = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM jobs WHERE status = 'CANCELLED'")
        cancelled_downloads = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('DOWNLOADING', 'PROCESSING')")
        active_downloads = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM jobs WHERE status = 'QUEUED'")
        queued_downloads = cursor.fetchone()[0]

        cursor.execute("SELECT COALESCE(SUM(downloaded_bytes), 0) FROM jobs")
        total_bytes = cursor.fetchone()[0]

        # Top extractors from media library
        cursor.execute(
            """
            SELECT COALESCE(extractor, 'Unknown') as ext, COUNT(*) as count
            FROM media_library
            GROUP BY ext
            ORDER BY count DESC
            LIMIT 5
            """
        )
        top_extractors = [{"name": r[0], "count": r[1]} for r in cursor.fetchall()]

        # Top containers from media library
        cursor.execute(
            """
            SELECT COALESCE(container, 'mp4') as cont, COUNT(*) as count
            FROM media_library
            GROUP BY cont
            ORDER BY count DESC
            LIMIT 5
            """
        )
        top_containers = [{"format": r[0].upper(), "count": r[1]} for r in cursor.fetchall()]

        # Daily download history (past 7 days)
        now = time.time()
        days_data = []
        for i in range(6, -1, -1):
            day_start = now - (i * 86400)
            day_end = day_start + 86400
            date_str = datetime.datetime.fromtimestamp(day_start).strftime("%b %d")
            cursor.execute(
                "SELECT COUNT(*) FROM jobs WHERE created_at >= ? AND created_at < ?",
                (day_start, day_end),
            )
            count = cursor.fetchone()[0]
            days_data.append({"date": date_str, "count": count})

    return StatisticsResponse(
        total_downloads=total_downloads,
        completed_downloads=completed_downloads,
        failed_downloads=failed_downloads,
        cancelled_downloads=cancelled_downloads,
        total_bytes_downloaded=total_bytes,
        total_formatted=FileService.format_bytes(total_bytes),
        active_downloads=active_downloads,
        queued_downloads=queued_downloads,
        top_extractors=top_extractors,
        top_containers=top_containers,
        downloads_by_day=days_data,
    )
