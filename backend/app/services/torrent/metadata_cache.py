"""
MetadataCache: Secure and persistent caching for BitTorrent metadata manifests.
Stores acquired metadata indexed by info_hash to allow instantaneous repeat analysis
and fast startup without redundant swarm DHT/tracker lookups.
"""

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import settings
from app.utils.logger import logger

# Strict 40-character hex pattern for BitTorrent info hashes
HEX_HASH_REGEX = re.compile(r"^[0-9a-fA-F]{40}$")


class MetadataCache:
    @staticmethod
    def _validate_hash(info_hash: str) -> str:
        ih = str(info_hash).strip().lower()
        if not HEX_HASH_REGEX.match(ih):
            raise ValueError(f"Invalid info hash for metadata cache: {info_hash}")
        return ih

    @classmethod
    def get_cache_dir(cls) -> Path:
        p = settings.torrent_metadata_path
        p.mkdir(parents=True, exist_ok=True)
        return p

    @classmethod
    def save(cls, info_hash: str, data: Dict[str, Any]) -> Path:
        """
        Persists metadata dict for a torrent info hash to disk.
        Sanitizes file paths to prevent directory traversal / cache poisoning.
        """
        ih = cls._validate_hash(info_hash)
        cache_dir = cls.get_cache_dir()
        target_file = cache_dir / f"{ih}.json"
        temp_file = cache_dir / f"{ih}.json.tmp"

        # Sanitize files list to prevent path traversal
        raw_files = data.get("files", [])
        clean_files: List[Dict[str, Any]] = []
        for idx, f in enumerate(raw_files):
            raw_path = f.get("path", f"file_{idx}")
            # Ensure path does not break out of sandbox
            clean_path = str(raw_path).replace("\\", "/").strip().lstrip("/")
            if ".." in clean_path.split("/"):
                clean_path = Path(clean_path).name  # Fall back to safe leaf name
            clean_files.append({
                "index": f.get("index", idx),
                "path": clean_path,
                "size": int(f.get("size", 0)),
            })

        payload = {
            "info_hash": ih,
            "name": str(data.get("name") or f"torrent_{ih[:10]}"),
            "acquired_at": float(data.get("acquired_at", time.time())),
            "total_size": int(data.get("total_size", 0)),
            "file_count": len(clean_files) if clean_files else int(data.get("file_count", 1)),
            "piece_count": int(data.get("piece_count", 0)),
            "piece_length": int(data.get("piece_length", 0)),
            "trackers": [str(t) for t in data.get("trackers", []) if t],
            "is_multi_file": bool(data.get("is_multi_file", len(clean_files) > 1)),
            "files": clean_files,
            "magnet_uri": data.get("magnet_uri"),
        }

        try:
            temp_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            temp_file.replace(target_file)
            logger.info(f"Persisted metadata cache for torrent [{ih}] ({payload['file_count']} files)")
            return target_file
        except Exception as e:
            logger.warning(f"Failed to persist metadata cache for [{ih}]: {e}")
            if temp_file.exists():
                temp_file.unlink(missing_ok=True)
            return target_file

    @classmethod
    def get(cls, info_hash: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves cached metadata for an info hash if present and valid.
        Returns None if cache does not exist or is corrupted.
        """
        try:
            ih = cls._validate_hash(info_hash)
        except ValueError:
            return None

        target_file = cls.get_cache_dir() / f"{ih}.json"
        if not target_file.exists():
            return None

        try:
            content = target_file.read_text(encoding="utf-8")
            data = json.loads(content)

            # Security validation: identity match
            if str(data.get("info_hash", "")).lower() != ih:
                logger.warning(f"Cache poisoning detected in {target_file}: info_hash mismatch")
                return None

            return data
        except Exception as e:
            logger.warning(f"Error reading metadata cache for [{ih}]: {e}")
            return None

    @classmethod
    def has(cls, info_hash: str) -> bool:
        try:
            ih = cls._validate_hash(info_hash)
            return (cls.get_cache_dir() / f"{ih}.json").exists()
        except ValueError:
            return False

    @classmethod
    def delete(cls, info_hash: str) -> bool:
        try:
            ih = cls._validate_hash(info_hash)
            target = cls.get_cache_dir() / f"{ih}.json"
            if target.exists():
                target.unlink()
                return True
        except Exception:
            pass
        return False
