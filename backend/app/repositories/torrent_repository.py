"""
Repository for persisting torrent records and file manifests in SQLite.
"""

import json
import time
from typing import Any, Dict, List, Optional
from app.db.database import get_db
from app.utils.logger import logger


class TorrentRepository:
    @classmethod
    def save_torrent(cls, data: Dict[str, Any]) -> None:
        """Creates or updates a torrent record."""
        now = time.time()
        trackers_json = json.dumps(data.get("trackers", [])) if isinstance(data.get("trackers"), list) else data.get("trackers")

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO torrents (
                    id, job_id, info_hash, name, magnet_uri, torrent_file_path,
                    total_size, downloaded_size, uploaded_size, ratio, status,
                    seeding_mode, seeding_until, download_dir, piece_count,
                    piece_length, trackers_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    job_id = excluded.job_id,
                    info_hash = excluded.info_hash,
                    name = excluded.name,
                    magnet_uri = excluded.magnet_uri,
                    torrent_file_path = excluded.torrent_file_path,
                    total_size = excluded.total_size,
                    downloaded_size = excluded.downloaded_size,
                    uploaded_size = excluded.uploaded_size,
                    ratio = excluded.ratio,
                    status = excluded.status,
                    seeding_mode = excluded.seeding_mode,
                    seeding_until = excluded.seeding_until,
                    download_dir = excluded.download_dir,
                    piece_count = excluded.piece_count,
                    piece_length = excluded.piece_length,
                    trackers_json = excluded.trackers_json,
                    updated_at = excluded.updated_at
                """,
                (
                    data["id"],
                    data.get("job_id"),
                    data["info_hash"].lower(),
                    data["name"],
                    data.get("magnet_uri"),
                    data.get("torrent_file_path"),
                    data.get("total_size", 0),
                    data.get("downloaded_size", 0),
                    data.get("uploaded_size", 0),
                    data.get("ratio", 0.0),
                    data.get("status", "QUEUED"),
                    data.get("seeding_mode", "stop"),
                    data.get("seeding_until"),
                    data.get("download_dir", ""),
                    data.get("piece_count", 0),
                    data.get("piece_length", 0),
                    trackers_json,
                    data.get("created_at", now),
                    now,
                ),
            )

    @classmethod
    def get_by_id(cls, torrent_id: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM torrents WHERE id = ?", (torrent_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return cls._row_to_dict(row)

    @classmethod
    def get_by_info_hash(cls, info_hash: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM torrents WHERE LOWER(info_hash) = ? ORDER BY created_at DESC LIMIT 1", (info_hash.lower(),))
            row = cursor.fetchone()
            if not row:
                return None
            return cls._row_to_dict(row)

    @classmethod
    def get_by_job_id(cls, job_id: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM torrents WHERE job_id = ? LIMIT 1", (job_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return cls._row_to_dict(row)

    @classmethod
    def list_all(cls, limit: int = 100) -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM torrents ORDER BY created_at DESC LIMIT ?", (limit,))
            return [cls._row_to_dict(r) for r in cursor.fetchall()]

    @classmethod
    def list_active(cls) -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM torrents
                WHERE status IN ('DOWNLOADING', 'PROCESSING', 'SEEDING', 'PAUSED')
                ORDER BY created_at ASC
                """
            )
            return [cls._row_to_dict(r) for r in cursor.fetchall()]

    @classmethod
    def delete_torrent(cls, torrent_id: str) -> None:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM torrents WHERE id = ?", (torrent_id,))

    # --- Torrent Files Manifest ---

    @classmethod
    def save_files(cls, torrent_id: str, files: List[Dict[str, Any]]) -> None:
        now = time.time()
        with get_db() as conn:
            cursor = conn.cursor()
            # Clear previous manifest entries for this torrent
            cursor.execute("DELETE FROM torrent_files WHERE torrent_id = ?", (torrent_id,))
            entries = []
            for f in files:
                file_id = f.get("id") or f"{torrent_id}_{f['index']}"
                entries.append((
                    file_id,
                    torrent_id,
                    f["index"],
                    f["path"],
                    f["size"],
                    1 if f.get("selected", True) else 0,
                    f.get("priority", "normal"),
                    f.get("downloaded_bytes", 0),
                    1 if f.get("is_completed", False) else 0,
                    now,
                ))
            cursor.executemany(
                """
                INSERT INTO torrent_files (
                    id, torrent_id, file_index, path, size, selected,
                    priority, downloaded_bytes, is_completed, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                entries,
            )

    @classmethod
    def get_files(cls, torrent_id: str) -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM torrent_files WHERE torrent_id = ? ORDER BY file_index ASC",
                (torrent_id,),
            )
            res = []
            for r in cursor.fetchall():
                d = dict(r)
                d["selected"] = bool(d["selected"])
                d["is_completed"] = bool(d["is_completed"])
                res.append(d)
            return res

    @staticmethod
    def _row_to_dict(row: Any) -> Dict[str, Any]:
        d = dict(row)
        if d.get("trackers_json"):
            try:
                d["trackers"] = json.loads(d["trackers_json"])
            except Exception:
                d["trackers"] = []
        else:
            d["trackers"] = []
        return d
