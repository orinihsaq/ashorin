import os
import re
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
from app.config import settings
from app.models.schemas import MediaItem, MediaListResponse, MediaStorageSummary
from app.repositories.media_repository import MediaRepository
from app.services.file_service import FileService
from app.utils.logger import logger

router = APIRouter(tags=["Media Library"])


@router.get("/api/library", response_model=MediaListResponse)
async def list_library(
    type: Optional[str] = Query(None, description="Filter by type: video, audio, playlist"),
    search: Optional[str] = Query(None, description="Search term in title, filename, uploader"),
    sort_by: str = Query("created_at", description="created_at, title, filesize, duration"),
    sort_order: str = Query("desc", description="asc or desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_favorite: Optional[bool] = Query(None),
    is_protected: Optional[bool] = Query(None),
    provider: Optional[str] = Query(None, description="Filter by provider: ytdlp, torrent, or all"),
):
    """Lists media items in the library with search, filtering, and pagination."""
    items_data, total = MediaRepository.list_media(
        media_type=type,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
        is_favorite=is_favorite,
        is_protected=is_protected,
        provider=provider,
    )

    items = [MediaItem(**d) for d in items_data]
    total_pages = max(1, (total + page_size - 1) // page_size)

    return MediaListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/api/library/storage", response_model=MediaStorageSummary)
async def get_storage_summary():
    """Returns storage analytics and disk usage breakdown."""
    summary = MediaRepository.get_storage_summary()
    return MediaStorageSummary(**summary)


@router.get("/api/library/{media_id}", response_model=MediaItem)
async def get_media_item(media_id: str):
    """Retrieves metadata for a specific media item."""
    item = MediaRepository.get_media(media_id)
    if not item:
        raise HTTPException(status_code=404, detail="Media item not found")
    return MediaItem(**item)


@router.post("/api/library/{media_id}/favorite")
async def toggle_favorite(media_id: str):
    """Toggles favorite status for a media item."""
    item = MediaRepository.get_media(media_id)
    if not item:
        raise HTTPException(status_code=404, detail="Media item not found")
    new_fav = MediaRepository.toggle_favorite(media_id)
    return {"status": "success", "is_favorite": new_fav}


@router.post("/api/library/{media_id}/protect")
async def toggle_protect(media_id: str):
    """Toggles protected status (exempts from automatic retention deletion)."""
    item = MediaRepository.get_media(media_id)
    if not item:
        raise HTTPException(status_code=404, detail="Media item not found")
    new_prot = MediaRepository.toggle_protected(media_id)
    return {"status": "success", "is_protected": new_prot}


@router.delete("/api/library/{media_id}")
async def delete_media_item(media_id: str):
    """Deletes a media item and its file from disk if not protected."""
    item = MediaRepository.get_media(media_id)
    if not item:
        raise HTTPException(status_code=404, detail="Media item not found")
    if item.get("is_protected"):
        raise HTTPException(status_code=400, detail="Cannot delete a protected media item. Unprotect it first.")

    try:
        MediaRepository.delete_media(media_id, delete_file=True)
        return {"status": "success", "message": "Media item deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/media/{media_id}/stream")
async def stream_media(media_id: str, request: Request):
    """
    Streams audio/video with HTTP 206 Partial Content support for seeking in HTML5 players.
    Guarantees path traversal containment within DOWNLOAD_DIR.
    """
    item = MediaRepository.get_media(media_id)
    if not item:
        raise HTTPException(status_code=404, detail="Media not found")

    rel_path = item.get("relative_path")
    if not rel_path:
        raise HTTPException(status_code=404, detail="File path missing")

    base_dir = settings.download_path.resolve()
    target = (base_dir / rel_path).resolve()

    # Path traversal check
    if not target.is_relative_to(base_dir) or not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Media file not found on disk")

    file_size = target.stat().st_size
    media_type = FileService.get_media_type(target.name)

    range_header = request.headers.get("range")
    if not range_header:
        # Full content response
        return FileResponse(
            str(target),
            media_type=media_type,
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_size),
            },
        )

    # Parse Range: bytes=start-end
    match = re.match(r"bytes=(\d+)-(\d*)", range_header)
    if not match:
        raise HTTPException(status_code=416, detail="Invalid Range header")

    start_str, end_str = match.groups()
    start = int(start_str)
    end = int(end_str) if end_str else file_size - 1

    if start >= file_size or end >= file_size or start > end:
        return Response(
            status_code=416,
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    chunk_size = (end - start) + 1

    def iter_file():
        with open(target, "rb") as f:
            f.seek(start)
            remaining = chunk_size
            while remaining > 0:
                read_bytes = min(remaining, 64 * 1024)
                data = f.read(read_bytes)
                if not data:
                    break
                remaining -= len(data)
                yield data

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(chunk_size),
        "Content-Type": media_type,
    }

    return StreamingResponse(iter_file(), status_code=206, headers=headers)


@router.get("/api/media/{media_id}/download")
async def download_media(media_id: str):
    """Direct browser download endpoint with RFC-compliant Content-Disposition."""
    item = MediaRepository.get_media(media_id)
    if not item:
        raise HTTPException(status_code=404, detail="Media not found")

    rel_path = item.get("relative_path")
    if not rel_path:
        raise HTTPException(status_code=404, detail="File path missing")

    base_dir = settings.download_path.resolve()
    target = (base_dir / rel_path).resolve()

    if not target.is_relative_to(base_dir) or not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Media file not found on disk")

    media_type = FileService.get_media_type(target.name)
    disposition = FileService.build_content_disposition(target.name)

    return FileResponse(
        str(target),
        media_type=media_type,
        headers={"Content-Disposition": disposition},
    )
