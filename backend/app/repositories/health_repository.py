import json
import time
import uuid
from typing import Any, Dict, List, Optional
from app.db.database import get_db
from app.utils.logger import logger


class HealthRepository:
    @classmethod
    def create_scan(cls, scan_id: Optional[str] = None, started_at: Optional[float] = None) -> str:
        s_id = scan_id or str(uuid.uuid4())
        start = started_at or time.time()
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO health_scans (
                    id, started_at, completed_at, status,
                    files_scanned, issues_found, issues_repaired,
                    storage_recoverable_bytes, summary_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (s_id, start, None, "RUNNING", 0, 0, 0, 0, None),
            )
        return s_id

    @classmethod
    def update_scan(cls, scan_id: str, updates: Dict[str, Any]) -> None:
        set_clauses = []
        params = []
        for k in ["completed_at", "status", "files_scanned", "issues_found", "issues_repaired", "storage_recoverable_bytes"]:
            if k in updates and updates[k] is not None:
                set_clauses.append(f"{k} = ?")
                params.append(updates[k])

        if "summary" in updates and updates["summary"] is not None:
            set_clauses.append("summary_json = ?")
            params.append(json.dumps(updates["summary"]))

        if not set_clauses:
            return

        params.append(scan_id)
        with get_db() as conn:
            conn.execute(f"UPDATE health_scans SET {', '.join(set_clauses)} WHERE id = ?", tuple(params))

    @classmethod
    def get_latest_scan(cls) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM health_scans ORDER BY started_at DESC LIMIT 1").fetchone()
            if not row:
                return None
            scan = dict(row)
            scan["summary"] = json.loads(scan["summary_json"]) if scan.get("summary_json") else {}
            scan["issues"] = cls.list_issues(scan_id=scan["id"], unresolved_only=False)
            return scan

    @classmethod
    def get_scan(cls, scan_id: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM health_scans WHERE id = ?", (scan_id,)).fetchone()
            if not row:
                return None
            scan = dict(row)
            scan["summary"] = json.loads(scan["summary_json"]) if scan.get("summary_json") else {}
            scan["issues"] = cls.list_issues(scan_id=scan_id, unresolved_only=False)
            return scan

    @classmethod
    def record_issues(cls, issues: List[Dict[str, Any]]) -> None:
        if not issues:
            return
        now = time.time()
        rows = []
        for iss in issues:
            iss_id = iss.get("id") or str(uuid.uuid4())
            details_str = json.dumps(iss.get("details", {})) if iss.get("details") else None
            rows.append((
                iss_id,
                iss["scan_id"],
                iss["issue_type"],
                iss.get("severity", "warning"),
                iss.get("media_id"),
                iss.get("file_path"),
                iss.get("title"),
                iss["description"],
                details_str,
                iss["recommended_action"],
                iss.get("recoverable_bytes", 0),
                0,
                None,
                None,
                now,
            ))

        with get_db() as conn:
            conn.executemany(
                """
                INSERT INTO health_issues (
                    id, scan_id, issue_type, severity, media_id, file_path,
                    title, description, details_json, recommended_action,
                    recoverable_bytes, is_resolved, resolved_at, resolution_action,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

    @classmethod
    def list_issues(
        cls,
        scan_id: Optional[str] = None,
        unresolved_only: bool = True,
        issue_type: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM health_issues WHERE 1=1"
        params = []
        if scan_id:
            query += " AND scan_id = ?"
            params.append(scan_id)
        if unresolved_only:
            query += " AND is_resolved = 0"
        if issue_type:
            query += " AND issue_type = ?"
            params.append(issue_type)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with get_db() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["is_resolved"] = bool(item.get("is_resolved", 0))
                item["details"] = json.loads(item["details_json"]) if item.get("details_json") else {}
                results.append(item)
            return results

    @classmethod
    def resolve_issue(cls, issue_id: str, action: str) -> bool:
        now = time.time()
        with get_db() as conn:
            cursor = conn.execute(
                """
                UPDATE health_issues SET
                    is_resolved = 1,
                    resolved_at = ?,
                    resolution_action = ?
                WHERE id = ?
                """,
                (now, action, issue_id),
            )
            return cursor.rowcount > 0

    @classmethod
    def resolve_issues(cls, issue_ids: List[str], action: str) -> int:
        if not issue_ids:
            return 0
        now = time.time()
        placeholders = ",".join("?" for _ in issue_ids)
        params = [now, action] + issue_ids
        with get_db() as conn:
            cursor = conn.execute(
                f"""
                UPDATE health_issues SET
                    is_resolved = 1,
                    resolved_at = ?,
                    resolution_action = ?
                WHERE id IN ({placeholders})
                """,
                tuple(params),
            )
            return cursor.rowcount
