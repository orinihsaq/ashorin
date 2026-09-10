import asyncio
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import analyze, download, files, jobs, system
from app.services.cleanup import CleanupService
from app.services.file_service import FileService
from app.services.updater import YtDlpUpdater
from app.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    FileService.ensure_directories()

    # Launch non-blocking background update check
    asyncio.create_task(YtDlpUpdater.startup_check())

    # Launch periodic file cleanup worker
    cleanup_task = asyncio.create_task(CleanupService.run_periodic_cleanup())

    yield

    # --- Shutdown ---
    logger.info("Shutting down application...")
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    logger.info("Shutdown complete.")


app = FastAPI(
    title="Media Downloader Pro",
    version=settings.APP_VERSION,
    description="Production-grade self-hosted media downloader powered by yt-dlp and FFmpeg.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(analyze.router)
app.include_router(download.router)
app.include_router(jobs.router)
app.include_router(files.router)
app.include_router(system.router)


@app.get("/health", tags=["Health"])
async def healthcheck():
    """Healthcheck endpoint for container orchestration and uptime monitoring."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": time.time(),
    }


# Frontend static files mounting and SPA fallback
frontend_dist_paths = [
    Path(__file__).parent.parent.parent / "frontend" / "dist",  # Local development
    Path("/app/frontend/dist"),                                  # Docker container
]

frontend_dist = next((p for p in frontend_dist_paths if p.exists() and (p / "index.html").exists()), None)

if frontend_dist:
    logger.info(f"Mounting frontend assets from: {frontend_dist}")
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Don't intercept API routes
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path == "health":
            raise HTTPException(status_code=404, detail="Not Found")

        file_path = frontend_dist / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(frontend_dist / "index.html"))
else:
    logger.info("No frontend build directory detected. Serving API only.")
