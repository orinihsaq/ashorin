import hashlib
import secrets
import sqlite3
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple
from app.db.database import get_db
from app.utils.logger import logger


class ApiKeyRepository:
    @staticmethod
    def hash_key(raw_key: str) -> str:
        """Computes SHA-256 hex digest of raw key."""
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @staticmethod
    def create_key(name: str) -> Tuple[str, Dict[str, Any]]:
        """
        Generates a new API key.
        Returns a tuple: (raw_key, key_record).
        The raw key is only returned here and never stored in plain text.
        """
        key_id = str(uuid.uuid4())
        raw_secret = secrets.token_hex(20)  # 40 hex chars
        raw_key = f"ash_live_{raw_secret}"
        key_hash = ApiKeyRepository.hash_key(raw_key)
        key_prefix = f"ash_live_{raw_secret[:6]}..."
        now = time.time()

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO api_keys (
                    id, name, key_hash, key_prefix, created_at, last_used_at, is_active
                ) VALUES (?, ?, ?, ?, ?, NULL, 1)
                """,
                (key_id, name, key_hash, key_prefix, now),
            )

        record = {
            "id": key_id,
            "name": name,
            "key_prefix": key_prefix,
            "created_at": now,
            "last_used_at": None,
            "is_active": True,
        }
        return raw_key, record

    @staticmethod
    def verify_key(raw_key: str) -> Optional[Dict[str, Any]]:
        """Verifies an incoming raw API key against stored SHA-256 hashes."""
        if not raw_key or not isinstance(raw_key, str):
            return None

        key_hash = ApiKeyRepository.hash_key(raw_key.strip())
        now = time.time()

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM api_keys WHERE key_hash = ? AND is_active = 1 LIMIT 1",
                (key_hash,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            key_id = row["id"]
            cursor.execute("UPDATE api_keys SET last_used_at = ? WHERE id = ?", (now, key_id))
            return ApiKeyRepository._row_to_dict(row)

    @staticmethod
    def list_keys() -> List[Dict[str, Any]]:
        """Lists all API keys (never returns the raw key or full hash)."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, key_prefix, created_at, last_used_at, is_active FROM api_keys ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [ApiKeyRepository._row_to_dict(r) for r in rows]

    @staticmethod
    def revoke_key(key_id: str) -> bool:
        """Revokes an API key by setting is_active = 0."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE api_keys SET is_active = 0 WHERE id = ?", (key_id,))
            return cursor.rowcount > 0

    @staticmethod
    def delete_key(key_id: str) -> bool:
        """Permanently deletes an API key."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
            return cursor.rowcount > 0

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        d["is_active"] = bool(d.get("is_active", 1))
        d.pop("key_hash", None)
        return d
