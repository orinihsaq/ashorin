"""
Dedicated BitTorrent Magnet URI parser and validator according to BEP 9, BEP 52, and BEP 53.

Crucial design principles:
1. Magnet URIs are URIs, NOT standard HTTP URLs or application/x-www-form-urlencoded forms.
2. Character '+' MUST NEVER be converted to spaces.
3. Multiple parameters of the same name (such as 'tr' for trackers, 'ws' for web seeds) are preserved.
4. The exact input payload is preserved without lossy reconstruction or double encoding.
5. Structured diagnostics are logged safely without exposing private tracker credentials/passkeys.
"""

import base64
import re
import urllib.parse
from typing import Any, Dict, List, Optional
from app.utils.errors import InvalidMagnetError, ValidationError
from app.utils.logger import logger


class MagnetParser:
    HEX_HASH_REGEX = re.compile(r"^[0-9a-fA-F]{40}$")
    BASE32_HASH_REGEX = re.compile(r"^[2-7a-zA-Z]{32}$")
    V2_HASH_REGEX = re.compile(r"^[0-9a-fA-F]{64}$")

    @classmethod
    def is_magnet_url(cls, url: str) -> bool:
        """
        Determines if an input string is a BitTorrent magnet URI.
        Checks for 'magnet:' scheme safely without HTTP URL parsing.
        """
        if not url or not isinstance(url, str):
            return False
        clean = url.strip()
        return clean.lower().startswith("magnet:")

    @classmethod
    def parse_magnet(cls, raw_magnet: str) -> Dict[str, Any]:
        """
        Parses and strictly validates a BitTorrent magnet URI.
        Preserves all query parameters, literal plus characters, and tracker URLs.
        
        Returns:
            Dict containing:
                - info_hash: 40-character lowercase hex string
                - name: display name (from dn or fallback)
                - trackers: list of tracker announce URLs (unquoted safely)
                - web_seeds: list of web seed URLs (from ws)
                - total_size: integer bytes if xl parameter was present
                - param_names: list of query parameter names present
                - original_uri: the raw input URI (stripped of leading/trailing whitespace)
                - canonical_uri: clean magnet URI with exact parameters
        """
        if not raw_magnet or not isinstance(raw_magnet, str) or not raw_magnet.strip():
            raise InvalidMagnetError("The URI is empty.")

        clean_magnet = raw_magnet.strip()

        if not clean_magnet.lower().startswith("magnet:"):
            raise InvalidMagnetError("Not a valid magnet URI: must begin with 'magnet:'.")

        # Strip 'magnet:' scheme
        after_scheme = clean_magnet[len("magnet:"):]
        if after_scheme.startswith("?"):
            query_part = after_scheme[1:]
        else:
            query_part = after_scheme

        if not query_part or not query_part.strip():
            raise InvalidMagnetError("The URI is empty.")

        # Parse query parameters manually to preserve '+' and avoid form-urlencoded mangling
        pairs = query_part.split("&")
        params: Dict[str, List[str]] = {}
        param_order: List[str] = []

        for pair in pairs:
            if not pair:
                continue
            if "=" in pair:
                k, v = pair.split("=", 1)
            else:
                k, v = pair, ""
            k_clean = k.strip()
            if not k_clean:
                continue
            if k_clean not in param_order:
                param_order.append(k_clean)
            params.setdefault(k_clean, []).append(v)

        # Extract & validate xt parameter (Exact Topic)
        xt_list = params.get("xt", [])
        if not xt_list:
            raise InvalidMagnetError("The link does not contain a valid BitTorrent info hash.")

        info_hash: Optional[str] = None
        for xt_val in xt_list:
            xt_clean = xt_val.strip()
            lower_xt = xt_clean.lower()

            # BEP 9: urn:btih:<hash>
            if lower_xt.startswith("urn:btih:"):
                raw_hash = xt_clean[len("urn:btih:"):].strip()

                # Case 1: 40-character hex SHA1
                if cls.HEX_HASH_REGEX.match(raw_hash):
                    info_hash = raw_hash.lower()
                    break

                # Case 2: 32-character base32 SHA1
                elif cls.BASE32_HASH_REGEX.match(raw_hash):
                    try:
                        padding = (8 - len(raw_hash) % 8) % 8
                        padded = (raw_hash.upper() + "=" * padding).encode("ascii")
                        decoded_bytes = base64.b32decode(padded)
                        if len(decoded_bytes) == 20:
                            info_hash = decoded_bytes.hex().lower()
                            break
                    except Exception:
                        pass

            # BEP 52: BitTorrent v2 multihash urn:btmh:1220<64-char-hex>
            elif lower_xt.startswith("urn:btmh:"):
                raw_hash = xt_clean[len("urn:btmh:"):].strip()
                if raw_hash.startswith("1220") and len(raw_hash) == 68 and cls.HEX_HASH_REGEX.match(raw_hash[4:44]):
                    info_hash = raw_hash[4:44].lower()
                    break
                elif cls.V2_HASH_REGEX.match(raw_hash):
                    info_hash = raw_hash[:40].lower()
                    break

        if not info_hash:
            raise InvalidMagnetError("The link does not contain a valid BitTorrent info hash.")

        # Extract Display Name (dn)
        name: Optional[str] = None
        dn_list = params.get("dn", [])
        if dn_list and dn_list[0].strip():
            raw_dn = dn_list[0].strip()
            # Unquote percent-encoding WITHOUT replacing '+' with space
            unquoted_dn = urllib.parse.unquote(raw_dn)
            # Remove dangerous path traversal and filesystem characters safely
            clean_name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', unquoted_dn).strip(" ._")
            if clean_name:
                name = clean_name

        if not name:
            name = f"magnet_{info_hash[:10]}"

        # Extract Trackers (tr) - preserve all without arbitrary truncation
        trackers: List[str] = []
        tr_list = params.get("tr", [])
        for tr_entry in tr_list:
            clean_tr = tr_entry.strip()
            if not clean_tr:
                continue
            # Safely unquote tracker URL while preserving '+'
            unquoted_tr = urllib.parse.unquote(clean_tr)
            if unquoted_tr and unquoted_tr not in trackers:
                lower_tr = unquoted_tr.lower()
                if lower_tr.startswith(("http://", "https://", "udp://", "wss://")):
                    trackers.append(unquoted_tr)

        # Extract Web Seeds (ws)
        web_seeds: List[str] = []
        ws_list = params.get("ws", [])
        for ws_entry in ws_list:
            clean_ws = ws_entry.strip()
            if clean_ws:
                unquoted_ws = urllib.parse.unquote(clean_ws)
                if unquoted_ws and unquoted_ws not in web_seeds:
                    web_seeds.append(unquoted_ws)

        # Extract Exact Length (xl) in bytes if provided
        size = 0
        xl_list = params.get("xl", [])
        if xl_list:
            try:
                size = max(0, int(xl_list[0].strip()))
            except ValueError:
                pass

        # Safe diagnostic logging: do NOT log full private trackers with passkeys
        logger.info(
            f"magnet_received scheme=magnet input_length={len(clean_magnet)} "
            f"info_hash={info_hash} param_names={param_order} tracker_count={len(trackers)} "
            f"validation=passed provider=torrent"
        )

        return {
            "info_hash": info_hash,
            "name": name,
            "trackers": trackers,
            "web_seeds": web_seeds,
            "total_size": size,
            "param_names": param_order,
            "original_uri": clean_magnet,
            "canonical_uri": clean_magnet,  # Preserve exact original payload without lossy re-encoding
        }

    @classmethod
    def validate(cls, raw_magnet: str) -> str:
        """
        Validates magnet URI and returns the clean string.
        Raises ValidationError with clear friendly error if invalid.
        """
        parsed = cls.parse_magnet(raw_magnet)
        return parsed["original_uri"]

    @classmethod
    def extract_info_hash(cls, raw_magnet: str) -> Optional[str]:
        """Safely extracts info hash or returns None without throwing."""
        try:
            return cls.parse_magnet(raw_magnet)["info_hash"]
        except Exception:
            return None


class MagnetValidator:
    """
    Dedicated BitTorrent magnet URI validator.
    Validates:
      - scheme == 'magnet:'
      - valid xt parameter with BEP 9, BEP 52, or base32 info hash
      - optional query parameters (dn, tr, ws, xl) preserved safely without data loss
      - rejects malformed or truncated magnet strings
    Does NOT call HTTP/HTTPS URL security validator or perform SSRF lookups.
    """
    @classmethod
    def validate(cls, raw_magnet: str) -> Dict[str, Any]:
        """Strictly validates magnet and returns parsed dictionary."""
        return MagnetParser.parse_magnet(raw_magnet)

    @classmethod
    def validate_uri(cls, raw_magnet: str) -> str:
        """Strictly validates magnet and returns untouched canonical URI string."""
        return cls.validate(raw_magnet)["original_uri"]

