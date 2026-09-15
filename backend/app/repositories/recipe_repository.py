import json
import time
import uuid
from typing import Any, Dict, List, Optional
from app.db.database import get_db
from app.utils.logger import logger


class RecipeRepository:
    @classmethod
    def create_recipe(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        recipe_id = data.get("id") or f"recipe_{uuid.uuid4().hex[:8]}"
        now = time.time()
        notify_events = data.get("notify_events", ["job.completed", "job.failed"])
        events_str = json.dumps(notify_events)

        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO recipes (
                    id, name, description, profile_id, storage_folder,
                    duplicate_policy, target_quality, minimum_quality,
                    upgrade_policy, retention_days, notify_events_json,
                    is_builtin, is_default, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    recipe_id,
                    data["name"],
                    data.get("description"),
                    data.get("profile_id", "recommended"),
                    data.get("storage_folder"),
                    data.get("duplicate_policy", "skip"),
                    data.get("target_quality", "best"),
                    data.get("minimum_quality", "720p"),
                    data.get("upgrade_policy", "ask"),
                    data.get("retention_days", 0),
                    events_str,
                    1 if data.get("is_builtin", False) else 0,
                    1 if data.get("is_default", False) else 0,
                    now,
                    now,
                ),
            )
        return cls.get_recipe(recipe_id)

    @classmethod
    def get_recipe(cls, recipe_id: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
            if not row:
                return None
            return cls._row_to_dict(row)

    @classmethod
    def list_recipes(cls) -> List[Dict[str, Any]]:
        with get_db() as conn:
            rows = conn.execute("SELECT * FROM recipes ORDER BY is_builtin DESC, is_default DESC, name ASC").fetchall()
            return [cls._row_to_dict(r) for r in rows]

    @classmethod
    def update_recipe(cls, recipe_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        existing = cls.get_recipe(recipe_id)
        if not existing:
            return None

        allowed = [
            "name", "description", "profile_id", "storage_folder",
            "duplicate_policy", "target_quality", "minimum_quality",
            "upgrade_policy", "retention_days"
        ]
        set_clauses = []
        params = []
        for k in allowed:
            if k in updates and updates[k] is not None:
                set_clauses.append(f"{k} = ?")
                params.append(updates[k])

        if "notify_events" in updates and updates["notify_events"] is not None:
            set_clauses.append("notify_events_json = ?")
            params.append(json.dumps(updates["notify_events"]))

        if not set_clauses:
            return existing

        set_clauses.append("updated_at = ?")
        params.append(time.time())
        params.append(recipe_id)

        with get_db() as conn:
            conn.execute(f"UPDATE recipes SET {', '.join(set_clauses)} WHERE id = ?", tuple(params))
        return cls.get_recipe(recipe_id)

    @classmethod
    def delete_recipe(cls, recipe_id: str) -> bool:
        recipe = cls.get_recipe(recipe_id)
        if not recipe or recipe.get("is_builtin"):
            return False  # Built-ins are protected

        with get_db() as conn:
            cursor = conn.execute("DELETE FROM recipes WHERE id = ? AND is_builtin = 0", (recipe_id,))
            return cursor.rowcount > 0

    @classmethod
    def clone_recipe(cls, recipe_id: str, new_name: str) -> Optional[Dict[str, Any]]:
        src = cls.get_recipe(recipe_id)
        if not src:
            return None
        clone_data = {
            "name": new_name,
            "description": f"Copy of {src['name']}",
            "profile_id": src["profile_id"],
            "storage_folder": src.get("storage_folder"),
            "duplicate_policy": src.get("duplicate_policy", "skip"),
            "target_quality": src.get("target_quality", "best"),
            "minimum_quality": src.get("minimum_quality", "720p"),
            "upgrade_policy": src.get("upgrade_policy", "ask"),
            "retention_days": src.get("retention_days", 0),
            "notify_events": src.get("notify_events", []),
            "is_builtin": False,
            "is_default": False,
        }
        return cls.create_recipe(clone_data)

    @classmethod
    def set_default_recipe(cls, recipe_id: str) -> bool:
        with get_db() as conn:
            conn.execute("UPDATE recipes SET is_default = 0")
            cursor = conn.execute("UPDATE recipes SET is_default = 1 WHERE id = ?", (recipe_id,))
            return cursor.rowcount > 0

    @classmethod
    def get_default_recipe(cls) -> Dict[str, Any]:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM recipes WHERE is_default = 1 LIMIT 1").fetchone()
            if row:
                return cls._row_to_dict(row)
            # Fallback to video_archive
            row = conn.execute("SELECT * FROM recipes WHERE id = 'video_archive' LIMIT 1").fetchone()
            if row:
                return cls._row_to_dict(row)
            # Ultimate fallback first available
            row = conn.execute("SELECT * FROM recipes LIMIT 1").fetchone()
            return cls._row_to_dict(row)

    @staticmethod
    def _row_to_dict(row: Any) -> Dict[str, Any]:
        d = dict(row)
        d["is_builtin"] = bool(d.get("is_builtin", 0))
        d["is_default"] = bool(d.get("is_default", 0))
        if d.get("notify_events_json"):
            try:
                d["notify_events"] = json.loads(d["notify_events_json"])
            except Exception:
                d["notify_events"] = []
        else:
            d["notify_events"] = []
        return d
