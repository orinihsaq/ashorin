import re
import sqlite3
import time
import urllib.parse
import uuid
from typing import Any, Dict, List, Optional
from app.db.database import get_db
from app.utils.logger import logger


class RuleRepository:
    @staticmethod
    def list_rules() -> List[Dict[str, Any]]:
        """Lists all automation rules, sorted by priority (highest first) then created_at."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM rules ORDER BY priority DESC, created_at ASC")
            rows = cursor.fetchall()
            return [RuleRepository._row_to_dict(r) for r in rows]

    @staticmethod
    def get_rule(rule_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single rule by ID."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM rules WHERE id = ?", (rule_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return RuleRepository._row_to_dict(row)

    @staticmethod
    def create_rule(
        name: str,
        condition_type: str,
        condition_value: str,
        profile_id: str,
        priority: int = 0,
        is_enabled: bool = True,
        rule_id: Optional[str] = None,
    ) -> str:
        """Creates a new automation rule."""
        rid = rule_id or f"rule_{str(uuid.uuid4())[:8]}"
        now = time.time()

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO rules (
                    id, name, condition_type, condition_value, profile_id, priority, is_enabled, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (rid, name, condition_type, condition_value, profile_id, priority, 1 if is_enabled else 0, now),
            )
        return rid

    @staticmethod
    def update_rule(rule_id: str, updates: Dict[str, Any]) -> bool:
        """Updates an existing automation rule."""
        existing = RuleRepository.get_rule(rule_id)
        if not existing:
            return False

        fields = []
        params = []
        if "name" in updates:
            fields.append("name = ?")
            params.append(updates["name"])
        if "condition_type" in updates:
            fields.append("condition_type = ?")
            params.append(updates["condition_type"])
        if "condition_value" in updates:
            fields.append("condition_value = ?")
            params.append(updates["condition_value"])
        if "profile_id" in updates:
            fields.append("profile_id = ?")
            params.append(updates["profile_id"])
        if "priority" in updates:
            fields.append("priority = ?")
            params.append(updates["priority"])
        if "is_enabled" in updates:
            fields.append("is_enabled = ?")
            params.append(1 if updates["is_enabled"] else 0)

        if not fields:
            return True

        params.append(rule_id)
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE rules SET {', '.join(fields)} WHERE id = ?", params)
        return True

    @staticmethod
    def delete_rule(rule_id: str) -> bool:
        """Deletes an automation rule."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
            return cursor.rowcount > 0

    @staticmethod
    def evaluate_rules(
        url: str,
        extractor: Optional[str] = None,
        title: Optional[str] = None,
        is_playlist: bool = False,
    ) -> Dict[str, Any]:
        """Evaluates enabled rules in priority order to determine optimal profile and reason."""
        rules = RuleRepository.list_rules()
        enabled_rules = [r for r in rules if r.get("is_enabled", True)]

        # Extract domain from URL
        domain = ""
        try:
            parsed = urllib.parse.urlparse(url)
            domain = (parsed.netloc or "").lower().split(":")[0]
        except Exception:
            pass

        for r in enabled_rules:
            ctype = r["condition_type"].lower().strip()
            cval = r["condition_value"].strip()
            matched = False

            if ctype == "domain":
                # Check if domain matches or ends with domain (e.g., soundcloud.com matches m.soundcloud.com)
                c_domain = cval.lower().replace("https://", "").replace("http://", "").split("/")[0]
                if domain == c_domain or domain.endswith("." + c_domain):
                    matched = True
            elif ctype == "extractor":
                if extractor and cval.lower() in extractor.lower():
                    matched = True
            elif ctype == "title_regex":
                if title:
                    try:
                        if re.search(cval, title, re.IGNORECASE):
                            matched = True
                    except Exception:
                        pass
            elif ctype == "is_playlist":
                expected = cval.lower() in ("true", "1", "yes")
                if bool(is_playlist) == expected:
                    matched = True

            if matched:
                return {
                    "matched": True,
                    "rule_id": r["id"],
                    "rule_name": r["name"],
                    "profile_id": r["profile_id"],
                    "reason": f"Matched rule '{r['name']}' ({r['condition_type']}: {r['condition_value']})",
                }

        return {
            "matched": False,
            "rule_id": None,
            "rule_name": None,
            "profile_id": None,
            "reason": "Default profile applied (no matching rule)",
        }

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        d["is_enabled"] = bool(d.get("is_enabled", 1))
        return d
