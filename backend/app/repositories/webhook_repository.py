import json
import sqlite3
import time
import uuid
from typing import Any, Dict, List, Optional
from app.db.database import get_db
from app.utils.logger import logger


class WebhookRepository:
    @staticmethod
    def list_webhooks() -> List[Dict[str, Any]]:
        """Lists all registered webhooks."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM webhooks ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [WebhookRepository._row_to_dict(r) for r in rows]

    @staticmethod
    def get_webhook(webhook_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single webhook by ID."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM webhooks WHERE id = ?", (webhook_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return WebhookRepository._row_to_dict(row)

    @staticmethod
    def create_webhook(url: str, events: List[str], signing_secret: Optional[str] = None) -> str:
        """Registers a new webhook."""
        webhook_id = str(uuid.uuid4())
        now = time.time()
        events_str = json.dumps(events)

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO webhooks (id, url, events_json, signing_secret, is_enabled, created_at)
                VALUES (?, ?, ?, ?, 1, ?)
                """,
                (webhook_id, url, events_str, signing_secret, now),
            )
        return webhook_id

    @staticmethod
    def update_webhook(webhook_id: str, updates: Dict[str, Any]) -> bool:
        """Updates an existing webhook."""
        existing = WebhookRepository.get_webhook(webhook_id)
        if not existing:
            return False

        fields = []
        params = []
        if "url" in updates:
            fields.append("url = ?")
            params.append(updates["url"])
        if "events" in updates:
            fields.append("events_json = ?")
            params.append(json.dumps(updates["events"]))
        if "signing_secret" in updates:
            fields.append("signing_secret = ?")
            params.append(updates["signing_secret"])
        if "is_enabled" in updates:
            fields.append("is_enabled = ?")
            params.append(1 if updates["is_enabled"] else 0)

        if not fields:
            return True

        params.append(webhook_id)
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE webhooks SET {', '.join(fields)} WHERE id = ?", params)
            return cursor.rowcount > 0

    @staticmethod
    def delete_webhook(webhook_id: str) -> bool:
        """Deletes a webhook and its delivery history."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM webhook_deliveries WHERE webhook_id = ?", (webhook_id,))
            cursor.execute("DELETE FROM webhooks WHERE id = ?", (webhook_id,))
            return cursor.rowcount > 0

    @staticmethod
    def log_delivery(
        webhook_id: str,
        event: str,
        payload_summary: Optional[str],
        status_code: Optional[int],
        success: bool,
        attempt_count: int = 1,
        error_message: Optional[str] = None,
    ) -> str:
        """Records a webhook delivery attempt in the database."""
        delivery_id = str(uuid.uuid4())
        now = time.time()

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO webhook_deliveries (
                    id, webhook_id, event, payload_summary, status_code, success, attempt_count, error_message, delivered_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    delivery_id,
                    webhook_id,
                    event,
                    payload_summary,
                    status_code,
                    1 if success else 0,
                    attempt_count,
                    error_message,
                    now,
                ),
            )
        return delivery_id

    @staticmethod
    def list_deliveries(webhook_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Lists recent webhook delivery logs."""
        with get_db() as conn:
            cursor = conn.cursor()
            if webhook_id:
                cursor.execute(
                    "SELECT * FROM webhook_deliveries WHERE webhook_id = ? ORDER BY delivered_at DESC LIMIT ?",
                    (webhook_id, limit),
                )
            else:
                cursor.execute(
                    "SELECT * FROM webhook_deliveries ORDER BY delivered_at DESC LIMIT ?",
                    (limit,),
                )
            rows = cursor.fetchall()
            return [
                {
                    "id": r["id"],
                    "webhook_id": r["webhook_id"],
                    "event": r["event"],
                    "payload_summary": r["payload_summary"],
                    "status_code": r["status_code"],
                    "success": bool(r["success"]),
                    "attempt_count": r["attempt_count"],
                    "error_message": r["error_message"],
                    "delivered_at": r["delivered_at"],
                }
                for r in rows
            ]

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        d["is_enabled"] = bool(d.get("is_enabled", 1))
        try:
            d["events"] = json.loads(d.get("events_json", "[]"))
        except Exception:
            d["events"] = []
        d.pop("events_json", None)
        return d
