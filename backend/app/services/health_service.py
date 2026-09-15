import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.config import settings
from app.db.database import get_db
from app.models.schemas import HealthScanModel, StorageForecastResponse
from app.repositories.health_repository import HealthRepository
from app.repositories.media_repository import MediaRepository
from app.services.webhook_service import WebhookService
from app.utils.formatting import format_bytes
from app.utils.logger import logger


class HealthService:
    @classmethod
    async def scan_library(cls) -> HealthScanModel:
        """
        Conducts a non-destructive audit of media library records and filesystem storage:
        - Missing files
        - Orphaned files
        - Duplicate media records
        - Incomplete/abandoned temp artifacts (.part, .ytdl)
        - Invalid metadata
        """
        scan_id = HealthRepository.create_scan()
        start_time = time.time()
        issues_to_record = []
        files_scanned = 0
        total_recoverable = 0

        # 1. Missing Files & Invalid Metadata Audit
        with get_db() as conn:
            records = conn.execute("SELECT * FROM media_library").fetchall()

        known_relative_paths = set()
        for r in records:
            item = dict(r)
            files_scanned += 1
            rel_path = item.get("relative_path")
            if rel_path:
                known_relative_paths.add(rel_path)
                abs_path = settings.download_path / rel_path
                if not abs_path.exists():
                    issues_to_record.append({
                        "scan_id": scan_id,
                        "issue_type": "missing_file",
                        "severity": "critical",
                        "media_id": item["id"],
                        "file_path": rel_path,
                        "title": item.get("title", "Unknown"),
                        "description": f"File recorded in database is missing on disk: {rel_path}",
                        "recommended_action": "Remove stale database reference or re-download",
                        "recoverable_bytes": 0,
                    })

            # Check invalid metadata
            if not item.get("container") or not item.get("filesize") or item["filesize"] <= 0:
                issues_to_record.append({
                    "scan_id": scan_id,
                    "issue_type": "invalid_metadata",
                    "severity": "warning",
                    "media_id": item["id"],
                    "file_path": rel_path,
                    "title": item.get("title", "Unknown"),
                    "description": "Library record is missing container format or valid filesize",
                    "recommended_action": "Re-index file metadata from disk",
                    "recoverable_bytes": 0,
                })

        # 2. Orphaned Records (Files on disk not tracked in media_library)
        download_dir = settings.download_path
        if download_dir.exists():
            for root, _, files in os.walk(download_dir):
                for f in files:
                    if f.endswith((".part", ".ytdl", ".temp")):
                        continue
                    full_p = Path(root) / f
                    try:
                        rel = str(full_p.relative_to(download_dir))
                        if rel not in known_relative_paths:
                            file_size = full_p.stat().st_size
                            issues_to_record.append({
                                "scan_id": scan_id,
                                "issue_type": "orphaned_record",
                                "severity": "info",
                                "file_path": rel,
                                "title": f.rsplit(".", 1)[0],
                                "description": f"File exists in download storage but is uncataloged in library: {rel}",
                                "recommended_action": "Catalog into media library or clean up",
                                "recoverable_bytes": file_size,
                            })
                    except Exception:
                        pass

        # 3. Duplicate Media Records
        with get_db() as conn:
            dup_rows = conn.execute(
                """
                SELECT source_url, COUNT(*) as cnt
                FROM media_library
                WHERE source_url IS NOT NULL AND source_url != ''
                GROUP BY source_url
                HAVING cnt > 1
                """
            ).fetchall()

            for d in dup_rows:
                source_url = d["source_url"]
                copies = conn.execute(
                    "SELECT id, title, relative_path, filesize, is_protected FROM media_library WHERE source_url = ?",
                    (source_url,),
                ).fetchall()

                copy_list = [dict(c) for c in copies]
                # Sort descending by size to identify best version
                copy_list.sort(key=lambda x: x.get("filesize") or 0, reverse=True)
                # Recoverable bytes is the sum of duplicate redundant copies
                dup_recoverable = sum(c.get("filesize") or 0 for c in copy_list[1:])
                total_recoverable += dup_recoverable

                issues_to_record.append({
                    "scan_id": scan_id,
                    "issue_type": "duplicate_media",
                    "severity": "warning",
                    "title": copy_list[0].get("title", "Duplicate Media"),
                    "description": f"Found {len(copy_list)} library entries referencing the same source: {source_url}",
                    "details": {"copies": copy_list},
                    "recommended_action": "Keep highest quality version and prune redundant duplicates",
                    "recoverable_bytes": dup_recoverable,
                })

        # 4. Incomplete Downloads / Abandoned Temp Files
        for scan_dir in [settings.temp_path, settings.download_path]:
            if scan_dir.exists():
                for root, _, files in os.walk(scan_dir):
                    for f in files:
                        if f.endswith((".part", ".ytdl", ".temp")):
                            full_p = Path(root) / f
                            try:
                                f_size = full_p.stat().st_size
                                total_recoverable += f_size
                                issues_to_record.append({
                                    "scan_id": scan_id,
                                    "issue_type": "incomplete_download",
                                    "severity": "warning",
                                    "file_path": str(full_p),
                                    "title": f,
                                    "description": f"Abandoned partial or temporary artifact: {f}",
                                    "recommended_action": "Safely delete temporary artifact",
                                    "recoverable_bytes": f_size,
                                })
                            except Exception:
                                pass

        # Record all issues
        HealthRepository.record_issues(issues_to_record)

        # Update Scan record
        summary = {
            "missing_count": len([i for i in issues_to_record if i["issue_type"] == "missing_file"]),
            "orphan_count": len([i for i in issues_to_record if i["issue_type"] == "orphaned_record"]),
            "duplicate_count": len([i for i in issues_to_record if i["issue_type"] == "duplicate_media"]),
            "incomplete_count": len([i for i in issues_to_record if i["issue_type"] == "incomplete_download"]),
            "invalid_metadata_count": len([i for i in issues_to_record if i["issue_type"] == "invalid_metadata"]),
        }

        HealthRepository.update_scan(scan_id, {
            "completed_at": time.time(),
            "status": "COMPLETED",
            "files_scanned": files_scanned,
            "issues_found": len(issues_to_record),
            "storage_recoverable_bytes": total_recoverable,
            "summary": summary,
        })

        WebhookService.dispatch_event("health.scan_completed", {
            "scan_id": scan_id,
            "files_scanned": files_scanned,
            "issues_found": len(issues_to_record),
            "storage_recoverable_formatted": format_bytes(total_recoverable),
        })

        scan_data = HealthRepository.get_scan(scan_id)
        scan_data["storage_recoverable_formatted"] = format_bytes(total_recoverable)
        return HealthScanModel(**scan_data)

    @classmethod
    async def repair_issues(
        cls, issue_ids: Optional[List[str]] = None, repair_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Safely repairs detected health issues:
        - Cleans incomplete temp files
        - Catalogs orphan files into library
        - Cleans stale missing database references
        NEVER removes protected files or favorites!
        """
        all_issues = HealthRepository.list_issues(unresolved_only=True, limit=500)
        repaired_count = 0
        freed_bytes = 0

        REPAIR_MAP = {
            "clean_incomplete": "incomplete_download",
            "reindex_orphans": "orphaned_record",
            "remove_stale": "missing_file",
        }
        target_issue_type = REPAIR_MAP.get(repair_type, repair_type) if repair_type and repair_type != "all" else None

        target_issues = [
            iss for iss in all_issues
            if (not issue_ids or iss["id"] in issue_ids) and (not target_issue_type or iss["issue_type"] == target_issue_type)
        ]

        for iss in target_issues:
            i_type = iss["issue_type"]
            action_taken = None

            # 1. Clean incomplete downloads
            if i_type == "incomplete_download" and iss.get("file_path"):
                p = Path(iss["file_path"])
                if p.exists() and p.suffix in [".part", ".ytdl", ".temp"]:
                    try:
                        sz = p.stat().st_size
                        p.unlink(missing_ok=True)
                        freed_bytes += sz
                        action_taken = "Deleted temporary artifact"
                        repaired_count += 1
                    except Exception as e:
                        logger.warning(f"Could not delete temp file {p}: {e}")

            # 2. Re-index orphaned records
            elif i_type == "orphaned_record" and iss.get("file_path"):
                full_p = settings.download_path / iss["file_path"]
                if full_p.exists():
                    try:
                        st = full_p.stat()
                        ext = full_p.suffix.lstrip(".").lower() or "mp4"
                        title = full_p.stem
                        MediaRepository.add_media({
                            "title": title,
                            "filename": full_p.name,
                            "relative_path": iss["file_path"],
                            "source_url": f"file://local/{iss['file_path']}",
                            "container": ext,
                            "filesize": st.st_size,
                            "downloaded_at": st.st_mtime,
                        })
                        action_taken = "Cataloged file into media library"
                        repaired_count += 1
                    except Exception as e:
                        logger.warning(f"Could not catalog orphan {full_p}: {e}")

            # 3. Remove stale records for missing files
            elif i_type == "missing_file" and iss.get("media_id"):
                media = MediaRepository.get_media(iss["media_id"])
                # Respect protection
                if media and not media.get("is_protected"):
                    with get_db() as conn:
                        conn.execute("DELETE FROM media_library WHERE id = ?", (iss["media_id"],))
                    action_taken = "Removed stale database record"
                    repaired_count += 1

            # 4. Repair invalid metadata
            elif i_type == "invalid_metadata" and iss.get("media_id") and iss.get("file_path"):
                full_p = settings.download_path / iss["file_path"]
                if full_p.exists():
                    st = full_p.stat()
                    ext = full_p.suffix.lstrip(".").lower() or "mp4"
                    with get_db() as conn:
                        conn.execute(
                            "UPDATE media_library SET container = ?, filesize = ? WHERE id = ?",
                            (ext, st.st_size, iss["media_id"]),
                        )
                    action_taken = "Updated container and filesize metadata"
                    repaired_count += 1

            if action_taken:
                HealthRepository.resolve_issue(iss["id"], action_taken)

        return {
            "status": "success",
            "repaired_count": repaired_count,
            "freed_bytes": freed_bytes,
            "freed_formatted": format_bytes(freed_bytes),
        }

    @classmethod
    def get_storage_forecast(cls) -> StorageForecastResponse:
        """Calculates storage consumption trends and forecast."""
        usage = shutil.disk_usage(str(settings.download_path))
        total = usage.total
        free = usage.free
        used = usage.used
        pct = round((used / total) * 100, 1)

        # Calculate daily download rate from completed jobs in past 7 days
        seven_days_ago = time.time() - (7 * 86400)
        with get_db() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(SUM(output_filesize), 0) as total_sz, COUNT(*) as cnt
                FROM jobs
                WHERE status = 'COMPLETED' AND completed_at >= ?
                """,
                (seven_days_ago,),
            ).fetchone()
            recent_bytes = row["total_sz"] or 0

        daily_rate = int(recent_bytes / 7) if recent_bytes > 0 else 0

        days_until_low = None
        low_space_threshold = 10 * 1024 * 1024 * 1024  # 10 GB
        if daily_rate > 0 and free > low_space_threshold:
            usable_free = free - low_space_threshold
            days_until_low = max(1, int(usable_free / daily_rate))

        # Potential recoverable from latest scan
        latest = HealthRepository.get_latest_scan()
        recoverable = latest.get("storage_recoverable_bytes", 0) if latest else 0

        if pct > 90:
            status_msg = "Critical storage state. Immediate cleanup recommended."
        elif pct > 75:
            status_msg = "Storage above 75%. Monitor growth and automatic syncs."
        else:
            status_msg = "Storage healthy and plenty of headroom available."

        return StorageForecastResponse(
            total_bytes=total,
            used_bytes=used,
            free_bytes=free,
            percent_used=pct,
            daily_download_rate_bytes=daily_rate,
            daily_download_rate_formatted=f"{format_bytes(daily_rate)}/day",
            days_until_low_space=days_until_low,
            potential_recoverable_bytes=recoverable,
            potential_recoverable_formatted=format_bytes(recoverable),
            status_summary=status_msg,
        )
