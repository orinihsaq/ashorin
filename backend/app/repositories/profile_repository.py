import json
import sqlite3
import time
import uuid
from typing import Any, Dict, List, Optional
from app.db.database import get_db
from app.models.schemas import DownloadConfig


class ProfileRepository:
    @staticmethod
    def list_profiles() -> List[Dict[str, Any]]:
        """Lists all download profiles, with default profile first."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM profiles ORDER BY is_default DESC, is_builtin DESC, name ASC")
            rows = cursor.fetchall()
            return [ProfileRepository._row_to_dict(r) for r in rows]

    @staticmethod
    def get_profile(profile_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single profile by ID."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return ProfileRepository._row_to_dict(row)

    @staticmethod
    def get_default_profile() -> Dict[str, Any]:
        """Gets the configured default profile, falling back to 'recommended'."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM profiles WHERE is_default = 1 LIMIT 1")
            row = cursor.fetchone()
            if row:
                return ProfileRepository._row_to_dict(row)

            cursor.execute("SELECT * FROM profiles WHERE id = 'recommended' LIMIT 1")
            row = cursor.fetchone()
            if row:
                return ProfileRepository._row_to_dict(row)

            cursor.execute("SELECT * FROM profiles LIMIT 1")
            row = cursor.fetchone()
            if row:
                return ProfileRepository._row_to_dict(row)

            # Fallback in-memory default
            return {
                "id": "recommended",
                "name": "Recommended",
                "description": "Balanced 1080p MP4 default profile.",
                "badge": "Default",
                "is_builtin": True,
                "is_default": True,
                "config": DownloadConfig().model_dump(),
                "created_at": time.time(),
                "updated_at": time.time(),
            }

    @staticmethod
    def create_profile(
        name: str,
        config: Dict[str, Any],
        description: Optional[str] = None,
        badge: Optional[str] = None,
        profile_id: Optional[str] = None,
    ) -> str:
        """Creates a new custom profile."""
        pid = profile_id or f"custom_{str(uuid.uuid4())[:8]}"
        now = time.time()
        cfg_str = json.dumps(config)

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO profiles (
                    id, name, description, badge, is_builtin, is_default, config_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 0, 0, ?, ?, ?)
                """,
                (pid, name, description, badge, cfg_str, now, now),
            )
        return pid

    @staticmethod
    def update_profile(profile_id: str, updates: Dict[str, Any]) -> bool:
        """Updates an existing profile. Built-in profiles cannot have config changed, only default status."""
        existing = ProfileRepository.get_profile(profile_id)
        if not existing:
            return False

        if existing["is_builtin"] and ("config" in updates or "name" in updates):
            raise ValueError("Built-in profiles cannot have their core settings modified.")

        fields = []
        params = []
        if "name" in updates and not existing["is_builtin"]:
            fields.append("name = ?")
            params.append(updates["name"])
        if "description" in updates:
            fields.append("description = ?")
            params.append(updates["description"])
        if "badge" in updates:
            fields.append("badge = ?")
            params.append(updates["badge"])
        if "config" in updates and not existing["is_builtin"]:
            fields.append("config_json = ?")
            params.append(json.dumps(updates["config"]))

        now = time.time()
        fields.append("updated_at = ?")
        params.append(now)
        params.append(profile_id)

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE profiles SET {', '.join(fields)} WHERE id = ?", params)

        if updates.get("is_default"):
            ProfileRepository.set_default_profile(profile_id)

        return True

    @staticmethod
    def delete_profile(profile_id: str) -> bool:
        """Deletes a custom profile. Built-in profiles cannot be deleted."""
        existing = ProfileRepository.get_profile(profile_id)
        if not existing:
            return False

        if existing["is_builtin"]:
            raise ValueError("Built-in profiles cannot be deleted.")

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
        return True

    @staticmethod
    def set_default_profile(profile_id: str) -> bool:
        """Marks one profile as default and unmarks all others."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE profiles SET is_default = 0")
            cursor.execute("UPDATE profiles SET is_default = 1 WHERE id = ?", (profile_id,))
            return cursor.rowcount > 0

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        d["is_builtin"] = bool(d.get("is_builtin", 0))
        d["is_default"] = bool(d.get("is_default", 0))
        try:
            d["config"] = json.loads(d.get("config_json", "{}"))
        except Exception:
            d["config"] = {}
        d.pop("config_json", None)
        return d
