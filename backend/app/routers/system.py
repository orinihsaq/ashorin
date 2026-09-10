from fastapi import APIRouter
from app.config import settings
from app.models.schemas import SystemInfoResponse
from app.services.ffmpeg import FFmpegService
from app.services.job_manager import job_manager
from app.services.updater import YtDlpUpdater
from app.services.yt_dlp import YtDlpService

router = APIRouter(prefix="/api/system", tags=["System"])


@router.get("", response_model=SystemInfoResponse)
async def get_system_info_endpoint() -> SystemInfoResponse:
    """
    Returns system runtime status, yt-dlp version, update availability,
    FFmpeg status, and queue statistics.
    """
    is_ffmpeg, ffmpeg_ver = await FFmpegService.get_version()
    ytdlp_ver = await YtDlpService.get_version()
    update_avail, _, latest_ver = await YtDlpUpdater.check_update_needed()

    import shutil
    storage_data = None
    try:
        total, used, free = shutil.disk_usage(settings.download_path)
        percent_used = round((used / total) * 100, 1) if total > 0 else 0.0
        storage_data = {
            "total_bytes": total,
            "free_bytes": free,
            "used_bytes": used,
            "percent_used": percent_used,
            "free_formatted": f"{free / (1024**3):.1f} GB",
            "total_formatted": f"{total / (1024**3):.1f} GB",
            "used_formatted": f"{used / (1024**3):.1f} GB",
        }
    except Exception:
        pass

    return SystemInfoResponse(
        app_name=settings.APP_NAME,
        app_version=settings.APP_VERSION,
        ytdlp_version=ytdlp_ver,
        latest_ytdlp_version=latest_ver,
        update_available=update_avail,
        ffmpeg_available=is_ffmpeg,
        ffmpeg_version=ffmpeg_ver,
        active_jobs=job_manager.get_active_count(),
        max_concurrent_downloads=settings.MAX_CONCURRENT_DOWNLOADS,
        download_retention=settings.DOWNLOAD_RETENTION,
        temp_retention=settings.TEMP_RETENTION,
        max_download_size=settings.MAX_DOWNLOAD_SIZE,
        storage_info=storage_data,
    )


@router.post("/update-ytdlp")
async def trigger_ytdlp_update_endpoint():
    """Manually triggers an online update for yt-dlp."""
    success, message = await YtDlpUpdater.update_ytdlp()
    new_ver = await YtDlpService.get_version()
    return {
        "success": success,
        "message": message,
        "current_version": new_ver,
    }
