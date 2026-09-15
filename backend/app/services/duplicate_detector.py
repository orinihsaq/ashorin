import urllib.parse
from typing import Any, Dict, Optional, Tuple
from app.db.database import get_db
from app.repositories.media_repository import MediaRepository
from app.utils.logger import logger


class DuplicateDetector:
    TRACKING_PARAMS = {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "si",
        "feature",
        "fbclid",
        "gclid",
        "ref",
        "ref_src",
        "igshid",
    }

    @classmethod
    def normalize_url(cls, raw_url: str) -> str:
        """Normalizes a URL by stripping tracking parameters, fragments, and standardizing host."""
        if not raw_url:
            return ""
        clean = raw_url.strip()
        if clean.lower().startswith("magnet:"):
            return clean
        try:
            parsed = urllib.parse.urlparse(clean)
            netloc = parsed.netloc.lower()
            if netloc.startswith("www."):
                netloc = netloc[4:]

            query_pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
            filtered_query = [
                (k, v) for k, v in query_pairs if k.lower() not in cls.TRACKING_PARAMS
            ]
            clean_query = urllib.parse.urlencode(filtered_query)

            clean_path = parsed.path.rstrip("/")
            return urllib.parse.urlunparse((parsed.scheme.lower(), netloc, clean_path, "", clean_query, ""))
        except Exception:
            return clean

    @classmethod
    def check_duplicate(
        cls,
        url: str,
        extractor: Optional[str] = None,
        media_id: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Checks whether a URL or media item is already present in the active queue or media library.
        For BitTorrent magnets, checks by info hash.
        Returns: (is_duplicate, reason, existing_record)
        """
        clean_url = url.strip()

        # Handle magnet URIs by extracting info hash
        if clean_url.lower().startswith("magnet:"):
            from app.services.torrent.magnet import MagnetParser
            info_hash = MagnetParser.extract_info_hash(clean_url)
            if info_hash:
                is_tor_dup, tor_reason, tor_rec = cls.check_torrent_duplicate(info_hash)
                if is_tor_dup:
                    return True, "Torrent already exists or is already queued.", tor_rec

        norm_url = cls.normalize_url(clean_url)

        # 1. Check in media library
        media = MediaRepository.find_by_source_url(url)
        if not media and norm_url != url:
            media = MediaRepository.find_by_source_url(norm_url)

        if media:
            return True, "Already in Media Library", media

        # 2. Check by extractor + media_id if available
        if extractor and media_id:
            media_by_id = MediaRepository.find_by_extractor_and_id(extractor, media_id)
            if media_by_id:
                return True, f"Already in Media Library ({extractor}:{media_id})", media_by_id

        # 3. Check in jobs database (completed or active)
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, title, status, output_filename, is_playlist FROM jobs
                WHERE url = ? AND status IN ('COMPLETED', 'DOWNLOADING', 'QUEUED', 'PROCESSING')
                LIMIT 1
                """,
                (url,),
            )
            job = cursor.fetchone()
            if not job and norm_url != url:
                cursor.execute(
                    """
                    SELECT id, title, status, output_filename, is_playlist FROM jobs
                    WHERE url = ? AND status IN ('COMPLETED', 'DOWNLOADING', 'QUEUED', 'PROCESSING')
                    LIMIT 1
                    """,
                    (norm_url,),
                )
                job = cursor.fetchone()

            if job:
                job_dict = dict(job)
                status = job_dict.get("status")
                if status == "COMPLETED":
                    return True, "Already downloaded in previous job", job_dict
                else:
                    return True, f"Currently active in queue ({status})", job_dict

        return False, None, None

    @classmethod
    def check_torrent_duplicate(
        cls,
        info_hash: str,
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Checks if a torrent with the given info_hash is already present or downloading."""
        if not info_hash:
            return False, None, None
        norm_hash = info_hash.lower().strip()
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, job_id, name, status FROM torrents
                WHERE LOWER(info_hash) = ?
                LIMIT 1
                """,
                (norm_hash,),
            )
            row = cursor.fetchone()
            if row:
                t = dict(row)
                return True, f"Torrent already exists or is already queued (active {t.get('status', 'DOWNLOADING')}).", t

            cursor.execute(
                """
                SELECT id, title, status, output_filename FROM jobs
                WHERE LOWER(info_hash) = ? AND status IN ('COMPLETED', 'SEEDING', 'DOWNLOADING', 'QUEUED', 'PAUSED', 'WAITING_FOR_METADATA', 'ACQUIRING_METADATA', 'READY')
                LIMIT 1
                """,
                (norm_hash,),
            )
            job = cursor.fetchone()
            if job:
                j = dict(job)
                return True, f"Torrent already exists or is already queued (active {j.get('status', 'QUEUED')}).", j

        return False, None, None
