import time
import uuid
from typing import Any, Dict, List, Optional
from app.db.database import get_db
from app.utils.logger import logger


class QualityRepository:
    @classmethod
    def upsert_target(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        media_id = data["media_id"]
        now = time.time()
        existing = cls.get_target_by_media(media_id)

        with get_db() as conn:
            if existing:
                conn.execute(
                    """
                    UPDATE quality_targets SET
                        current_height = COALESCE(?, current_height),
                        current_fps = COALESCE(?, current_fps),
                        current_filesize = COALESCE(?, current_filesize),
                        target_quality = ?,
                        minimum_quality = ?,
                        upgrade_policy = ?,
                        updated_at = ?
                    WHERE media_id = ?
                    """,
                    (
                        data.get("current_height"),
                        data.get("current_fps"),
                        data.get("current_filesize"),
                        data.get("target_quality", "1080p"),
                        data.get("minimum_quality", "720p"),
                        data.get("upgrade_policy", "ask"),
                        now,
                        media_id,
                    ),
                )
            else:
                target_id = str(uuid.uuid4())
                conn.execute(
                    """
                    INSERT INTO quality_targets (
                        id, media_id, current_height, current_fps, current_filesize,
                        target_quality, minimum_quality, upgrade_policy,
                        upgrade_available, upgrade_height, upgrade_filesize,
                        upgrade_source_url, status, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        target_id,
                        media_id,
                        data.get("current_height"),
                        data.get("current_fps"),
                        data.get("current_filesize"),
                        data.get("target_quality", "1080p"),
                        data.get("minimum_quality", "720p"),
                        data.get("upgrade_policy", "ask"),
                        0,
                        None,
                        None,
                        None,
                        "PENDING",
                        now,
                    ),
                )
        return cls.get_target_by_media(media_id)

    @classmethod
    def get_target_by_media(cls, media_id: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM quality_targets WHERE media_id = ?", (media_id,)).fetchone()
            if not row:
                return None
            res = dict(row)
            res["upgrade_available"] = bool(res.get("upgrade_available", 0))
            return res

    @classmethod
    def mark_upgrade_available(
        cls, media_id: str, upgrade_height: int, upgrade_filesize: Optional[int], upgrade_source_url: str
    ) -> None:
        now = time.time()
        with get_db() as conn:
            conn.execute(
                """
                UPDATE quality_targets SET
                    upgrade_available = 1,
                    upgrade_height = ?,
                    upgrade_filesize = ?,
                    upgrade_source_url = ?,
                    status = 'AVAILABLE',
                    updated_at = ?
                WHERE media_id = ?
                """,
                (upgrade_height, upgrade_filesize, upgrade_source_url, now, media_id),
            )

    @classmethod
    def list_available_upgrades(cls) -> List[Dict[str, Any]]:
        with get_db() as conn:
            query = """
            SELECT qt.*, m.title, m.filename, m.relative_path, m.source_url, m.container
            FROM quality_targets qt
            JOIN media_library m ON qt.media_id = m.id
            WHERE qt.upgrade_available = 1 AND qt.status = 'AVAILABLE'
            ORDER BY qt.updated_at DESC
            """
            rows = conn.execute(query).fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["upgrade_available"] = bool(item.get("upgrade_available", 0))
                results.append(item)
            return results

    @classmethod
    def update_upgrade_status(cls, media_id: str, status: str) -> bool:
        now = time.time()
        with get_db() as conn:
            cursor = conn.execute(
                """
                UPDATE quality_targets SET
                    status = ?,
                    upgrade_available = CASE WHEN ? = 'UPGRADED' OR ? = 'REJECTED' THEN 0 ELSE upgrade_available END,
                    updated_at = ?
                WHERE media_id = ?
                """,
                (status, status, status, now, media_id),
            )
            return cursor.rowcount > 0
