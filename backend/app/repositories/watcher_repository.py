import json
import time
import uuid
from typing import Any, Dict, List, Optional
from app.db.database import get_db
from app.utils.logger import logger


INTERVAL_PRESETS: Dict[str, int] = {
    "hourly": 3600,
    "every_3_hours": 10800,
    "every_6_hours": 21600,
    "every_12_hours": 43200,
    "daily": 86400,
    "weekly": 604800,
}


class WatcherRepository:
    @classmethod
    def create_watcher(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        watcher_id = str(uuid.uuid4())
        now = time.time()
        schedule = data.get("schedule", "every_6_hours")
        interval_secs = data.get("interval_seconds") or INTERVAL_PRESETS.get(schedule, 21600)
        next_check = now + interval_secs

        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO watchers (
                    id, name, source_url, source_type, schedule, interval_seconds,
                    status, profile_id, recipe_id, target_quality, minimum_quality,
                    upgrade_policy, duplicate_policy, destination_rule, download_new,
                    notify_new, notify_completed, notify_failed, items_tracked, items_downloaded,
                    last_checked, next_check, last_sync_result, consecutive_failures, last_error,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    watcher_id,
                    data["name"],
                    data["source_url"],
                    data.get("source_type", "playlist"),
                    schedule,
                    interval_secs,
                    data.get("status", "ACTIVE"),
                    data.get("profile_id", "recommended"),
                    data.get("recipe_id"),
                    data.get("target_quality", "1080p"),
                    data.get("minimum_quality", "720p"),
                    data.get("upgrade_policy", "ask"),
                    data.get("duplicate_policy", "skip"),
                    data.get("destination_rule"),
                    1 if data.get("download_new", True) else 0,
                    1 if data.get("notify_new", True) else 0,
                    1 if data.get("notify_completed", True) else 0,
                    1 if data.get("notify_failed", True) else 0,
                    0,
                    0,
                    None,
                    next_check,
                    None,
                    0,
                    None,
                    now,
                    now,
                ),
            )
        return cls.get_watcher(watcher_id)

    @classmethod
    def get_watcher(cls, watcher_id: str, include_runs: bool = True) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM watchers WHERE id = ?", (watcher_id,)).fetchone()
            if not row:
                return None
            watcher = dict(row)
            watcher["download_new"] = bool(watcher.get("download_new", 1))
            watcher["notify_new"] = bool(watcher.get("notify_new", 1))
            watcher["notify_completed"] = bool(watcher.get("notify_completed", 1))
            watcher["notify_failed"] = bool(watcher.get("notify_failed", 1))

            if include_runs:
                watcher["recent_runs"] = cls.get_recent_runs(watcher_id, limit=5)
            else:
                watcher["recent_runs"] = []
            return watcher

    @classmethod
    def list_watchers(cls, status: Optional[str] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM watchers"
        params = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC"

        with get_db() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["download_new"] = bool(item.get("download_new", 1))
                item["notify_new"] = bool(item.get("notify_new", 1))
                item["notify_completed"] = bool(item.get("notify_completed", 1))
                item["notify_failed"] = bool(item.get("notify_failed", 1))
                item["recent_runs"] = cls.get_recent_runs(item["id"], limit=3)
                results.append(item)
            return results

    @classmethod
    def update_watcher(cls, watcher_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        allowed_fields = [
            "name", "schedule", "interval_seconds", "status", "profile_id",
            "recipe_id", "target_quality", "minimum_quality", "upgrade_policy",
            "duplicate_policy", "destination_rule", "download_new", "notify_new",
            "notify_completed", "notify_failed", "items_tracked", "items_downloaded",
            "last_checked", "next_check", "last_sync_result", "consecutive_failures",
            "last_error"
        ]
        set_clauses = []
        params = []
        for k, v in updates.items():
            if k in allowed_fields:
                if isinstance(v, bool):
                    v = 1 if v else 0
                set_clauses.append(f"{k} = ?")
                params.append(v)

        if not set_clauses:
            return cls.get_watcher(watcher_id)

        set_clauses.append("updated_at = ?")
        params.append(time.time())
        params.append(watcher_id)

        with get_db() as conn:
            conn.execute(f"UPDATE watchers SET {', '.join(set_clauses)} WHERE id = ?", tuple(params))
        return cls.get_watcher(watcher_id)

    @classmethod
    def delete_watcher(cls, watcher_id: str) -> bool:
        with get_db() as conn:
            cursor = conn.execute("DELETE FROM watchers WHERE id = ?", (watcher_id,))
            return cursor.rowcount > 0

    @classmethod
    def set_watcher_status(cls, watcher_id: str, status: str) -> bool:
        with get_db() as conn:
            cursor = conn.execute(
                "UPDATE watchers SET status = ?, updated_at = ? WHERE id = ?",
                (status, time.time(), watcher_id),
            )
            return cursor.rowcount > 0

    @classmethod
    def record_run(cls, run_data: Dict[str, Any]) -> str:
        run_id = str(uuid.uuid4())
        details_str = json.dumps(run_data.get("details", {})) if run_data.get("details") else None

        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO watcher_runs (
                    id, watcher_id, started_at, completed_at, status,
                    items_seen, new_items, duplicates, upgrades, queued,
                    failed, details_json, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    run_data["watcher_id"],
                    run_data.get("started_at", time.time()),
                    run_data.get("completed_at"),
                    run_data.get("status", "RUNNING"),
                    run_data.get("items_seen", 0),
                    run_data.get("new_items", 0),
                    run_data.get("duplicates", 0),
                    run_data.get("upgrades", 0),
                    run_data.get("queued", 0),
                    run_data.get("failed", 0),
                    details_str,
                    run_data.get("error"),
                ),
            )
        return run_id

    @classmethod
    def update_run(cls, run_id: str, updates: Dict[str, Any]) -> None:
        set_clauses = []
        params = []
        for k in ["completed_at", "status", "items_seen", "new_items", "duplicates", "upgrades", "queued", "failed", "error"]:
            if k in updates:
                set_clauses.append(f"{k} = ?")
                params.append(updates[k])
        if "details" in updates:
            set_clauses.append("details_json = ?")
            params.append(json.dumps(updates["details"]))

        if not set_clauses:
            return

        params.append(run_id)
        with get_db() as conn:
            conn.execute(f"UPDATE watcher_runs SET {', '.join(set_clauses)} WHERE id = ?", tuple(params))

    @classmethod
    def get_recent_runs(cls, watcher_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM watcher_runs WHERE watcher_id = ? ORDER BY started_at DESC LIMIT ?",
                (watcher_id, limit),
            ).fetchall()
            results = []
            for r in rows:
                item = dict(r)
                if item.get("details_json"):
                    try:
                        item["details"] = json.loads(item["details_json"])
                    except Exception:
                        item["details"] = {}
                else:
                    item["details"] = {}
                results.append(item)
            return results

    @classmethod
    def get_due_watchers(cls, now: Optional[float] = None) -> List[Dict[str, Any]]:
        check_time = now or time.time()
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM watchers WHERE status = 'ACTIVE' AND (next_check IS NULL OR next_check <= ?)",
                (check_time,),
            ).fetchall()
            return [dict(r) for r in rows]

    @classmethod
    def get_watcher_stats(cls) -> Dict[str, Any]:
        with get_db() as conn:
            total = conn.execute("SELECT COUNT(*) FROM watchers").fetchone()[0]
            active = conn.execute("SELECT COUNT(*) FROM watchers WHERE status = 'ACTIVE'").fetchone()[0]
            items_tracked = conn.execute("SELECT COALESCE(SUM(items_tracked), 0) FROM watchers").fetchone()[0]
            items_downloaded = conn.execute("SELECT COALESCE(SUM(items_downloaded), 0) FROM watchers").fetchone()[0]
            return {
                "total_watchers": total,
                "active_watchers": active,
                "items_tracked": items_tracked,
                "items_downloaded": items_downloaded,
            }
