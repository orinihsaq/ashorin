import os
import shutil
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from app.config import settings
from app.db.database import get_db
from app.services.file_service import FileService
from app.utils.logger import logger


class MediaRepository:
    @staticmethod
    def add_media(data: Dict[str, Any]) -> str:
        """Inserts a new media record into media_library."""
        media_id = data.get("id") or str(uuid.uuid4())
        now = time.time()
        created_at = data.get("created_at") or now
        downloaded_at = data.get("downloaded_at") or now
        source_provider = data.get("source_provider") or "ytdlp"
        torrent_id = data.get("torrent_id")

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO media_library (
                    id, job_id, title, filename, relative_path, source_url,
                    extractor, media_id, uploader, playlist_name, duration,
                    duration_string, resolution, container, filesize,
                    thumbnail_url, is_favorite, is_protected, created_at,
                    downloaded_at, user_id, source_provider, torrent_id
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    filename=excluded.filename,
                    relative_path=excluded.relative_path,
                    filesize=excluded.filesize,
                    thumbnail_url=excluded.thumbnail_url,
                    source_provider=excluded.source_provider,
                    torrent_id=excluded.torrent_id
                """,
                (
                    media_id,
                    data.get("job_id"),
                    data.get("title", "Untitled"),
                    data.get("filename", ""),
                    data.get("relative_path", ""),
                    data.get("source_url", ""),
                    data.get("extractor"),
                    data.get("media_id"),
                    data.get("uploader"),
                    data.get("playlist_name"),
                    data.get("duration"),
                    data.get("duration_string"),
                    data.get("resolution"),
                    data.get("container", "mp4"),
                    data.get("filesize", 0),
                    data.get("thumbnail_url"),
                    1 if data.get("is_favorite") else 0,
                    1 if data.get("is_protected") else 0,
                    created_at,
                    downloaded_at,
                    data.get("user_id", "default"),
                    source_provider,
                    torrent_id,
                ),
            )
        return media_id

    save_media_item = add_media

    @staticmethod
    def get_media(media_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single media item by ID."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM media_library WHERE id = ?", (media_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return MediaRepository._row_to_dict(row)

    @staticmethod
    def find_by_source_url(source_url: str) -> Optional[Dict[str, Any]]:
        """Finds existing media item matching the source URL."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM media_library WHERE source_url = ? LIMIT 1", (source_url,))
            row = cursor.fetchone()
            if not row:
                return None
            return MediaRepository._row_to_dict(row)

    @staticmethod
    def find_by_extractor_and_id(extractor: str, media_id: str) -> Optional[Dict[str, Any]]:
        """Finds existing media item by extractor name and remote media ID."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM media_library WHERE extractor = ? AND media_id = ? LIMIT 1",
                (extractor, media_id),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return MediaRepository._row_to_dict(row)

    @staticmethod
    def list_media(
        media_type: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20,
        is_favorite: Optional[bool] = None,
        is_protected: Optional[bool] = None,
        provider: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Lists and filters media library items with pagination."""
        query = "SELECT * FROM media_library WHERE 1=1"
        count_query = "SELECT COUNT(*) FROM media_library WHERE 1=1"
        params: List[Any] = []

        if provider == "ytdlp":
            query += " AND (source_provider = 'ytdlp' OR source_provider IS NULL)"
            count_query += " AND (source_provider = 'ytdlp' OR source_provider IS NULL)"
        elif provider == "torrent":
            query += " AND source_provider = 'torrent'"
            count_query += " AND source_provider = 'torrent'"

        if media_type == "audio":
            query += " AND (container IN ('mp3', 'm4a', 'wav', 'flac', 'opus', 'aac', 'ogg') OR playlist_name IS NULL AND container IN ('mp3', 'm4a', 'wav', 'flac', 'opus'))"
            count_query += " AND (container IN ('mp3', 'm4a', 'wav', 'flac', 'opus', 'aac', 'ogg') OR playlist_name IS NULL AND container IN ('mp3', 'm4a', 'wav', 'flac', 'opus'))"
        elif media_type == "video":
            query += " AND container NOT IN ('mp3', 'm4a', 'wav', 'flac', 'opus', 'aac', 'ogg') AND playlist_name IS NULL"
            count_query += " AND container NOT IN ('mp3', 'm4a', 'wav', 'flac', 'opus', 'aac', 'ogg') AND playlist_name IS NULL"
        elif media_type == "playlist":
            query += " AND playlist_name IS NOT NULL"
            count_query += " AND playlist_name IS NOT NULL"

        if is_favorite is not None:
            val = 1 if is_favorite else 0
            query += " AND is_favorite = ?"
            count_query += " AND is_favorite = ?"
            params.append(val)

        if is_protected is not None:
            val = 1 if is_protected else 0
            query += " AND is_protected = ?"
            count_query += " AND is_protected = ?"
            params.append(val)

        if search:
            search_param = f"%{search.strip()}%"
            query += " AND (title LIKE ? OR filename LIKE ? OR uploader LIKE ? OR playlist_name LIKE ?)"
            count_query += " AND (title LIKE ? OR filename LIKE ? OR uploader LIKE ? OR playlist_name LIKE ?)"
            params.extend([search_param, search_param, search_param, search_param])

        allowed_sorts = {
            "created_at": "created_at",
            "title": "title",
            "filesize": "filesize",
            "duration": "duration",
        }
        col = allowed_sorts.get(sort_by, "created_at")
        direction = "ASC" if sort_order.lower() == "asc" else "DESC"

        query += f" ORDER BY {col} {direction}"
        offset = max(0, (page - 1) * page_size)
        query += f" LIMIT {max(1, page_size)} OFFSET {offset}"

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]

            cursor.execute(query, params)
            rows = cursor.fetchall()
            items = [MediaRepository._row_to_dict(r) for r in rows]

        return items, total

    @staticmethod
    def toggle_favorite(media_id: str) -> bool:
        """Toggles the favorite flag for a media item."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE media_library SET is_favorite = CASE WHEN is_favorite = 1 THEN 0 ELSE 1 END WHERE id = ?",
                (media_id,),
            )
            cursor.execute("SELECT is_favorite FROM media_library WHERE id = ?", (media_id,))
            row = cursor.fetchone()
            return bool(row[0]) if row else False

    @staticmethod
    def toggle_protected(media_id: str) -> bool:
        """Toggles the protected flag for a media item."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE media_library SET is_protected = CASE WHEN is_protected = 1 THEN 0 ELSE 1 END WHERE id = ?",
                (media_id,),
            )
            cursor.execute("SELECT is_protected FROM media_library WHERE id = ?", (media_id,))
            row = cursor.fetchone()
            return bool(row[0]) if row else False

    @staticmethod
    def delete_media(media_id: str, delete_file: bool = True) -> bool:
        """Deletes a media record and optionally its file from disk if not protected."""
        item = MediaRepository.get_media(media_id)
        if not item:
            return False

        if item.get("is_protected"):
            raise ValueError("Media item is protected against deletion.")

        if delete_file and item.get("relative_path"):
            target_path = settings.download_path / item["relative_path"]
            try:
                resolved = target_path.resolve()
                if resolved.is_relative_to(settings.download_path.resolve()):
                    if resolved.exists():
                        if resolved.is_file():
                            resolved.unlink()
                        elif resolved.is_dir():
                            shutil.rmtree(resolved, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Error removing media file {target_path}: {e}")

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM media_library WHERE id = ?", (media_id,))
            cursor.execute("DELETE FROM media_tags WHERE media_id = ?", (media_id,))

        return True

    @staticmethod
    def get_storage_summary() -> Dict[str, Any]:
        """Calculates media count, size breakdown, and free disk space."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*), COALESCE(SUM(filesize), 0) FROM media_library")
            total_files, total_bytes = cursor.fetchone()

            cursor.execute(
                """
                SELECT COUNT(*), COALESCE(SUM(filesize), 0)
                FROM media_library
                WHERE container IN ('mp3', 'm4a', 'wav', 'flac', 'opus', 'aac', 'ogg')
                """
            )
            audio_count, audio_bytes = cursor.fetchone()

            cursor.execute(
                """
                SELECT COUNT(*), COALESCE(SUM(filesize), 0)
                FROM media_library
                WHERE playlist_name IS NOT NULL
                """
            )
            playlists_count, playlists_bytes = cursor.fetchone()

            videos_count = max(0, total_files - audio_count)
            videos_bytes = max(0, total_bytes - audio_bytes)

        download_dir = settings.download_path
        disk_free = 0
        disk_total = 0
        try:
            stat = shutil.disk_usage(download_dir)
            disk_free = stat.free
            disk_total = stat.total
        except Exception:
            pass

        return {
            "total_files": total_files,
            "total_bytes": total_bytes,
            "total_formatted": FileService.format_bytes(total_bytes),
            "videos_count": videos_count,
            "videos_bytes": videos_bytes,
            "audio_count": audio_count,
            "audio_bytes": audio_bytes,
            "playlists_count": playlists_count,
            "playlists_bytes": playlists_bytes,
            "disk_free_bytes": disk_free,
            "disk_total_bytes": disk_total,
            "disk_free_formatted": FileService.format_bytes(disk_free),
        }

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        d["is_favorite"] = bool(d.get("is_favorite", 0))
        d["is_protected"] = bool(d.get("is_protected", 0))
        d["filesize_formatted"] = FileService.format_bytes(d.get("filesize", 0))
        d["stream_url"] = f"/api/media/{d['id']}/stream"
        d["download_url"] = f"/api/media/{d['id']}/download"
        d["source_provider"] = d.get("source_provider") or "ytdlp"
        d["torrent_id"] = d.get("torrent_id")
        return d
