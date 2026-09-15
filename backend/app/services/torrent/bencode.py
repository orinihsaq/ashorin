"""
Lightweight, robust, pure-Python Bencode decoder and encoder.
Includes security limits for recursion depth and maximum byte string length.
"""

import hashlib
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from app.utils.errors import ValidationError


class BencodeError(ValidationError):
    """Raised when parsing malformed or malicious bencoded content."""
    pass


MAX_RECURSION_DEPTH = 30
MAX_STRING_LENGTH = 50 * 1024 * 1024  # 50 MB safety cap per byte string


def bencode_decode(data: bytes) -> Any:
    """Decodes a bencoded byte sequence into Python structures."""
    if not isinstance(data, (bytes, bytearray)):
        raise BencodeError("Bencode input must be bytes or bytearray.")

    def _decode_at(idx: int, depth: int) -> Tuple[Any, int]:
        if depth > MAX_RECURSION_DEPTH:
            raise BencodeError(f"Exceeded maximum bencode nesting depth of {MAX_RECURSION_DEPTH}.")
        if idx >= len(data):
            raise BencodeError("Unexpected end of bencoded buffer.")

        char = data[idx:idx + 1]

        # Integer: i<integer>e
        if char == b"i":
            end = data.find(b"e", idx + 1)
            if end == -1:
                raise BencodeError("Unterminated bencoded integer.")
            int_str = data[idx + 1:end]
            if not int_str or (int_str.startswith(b"-0") or (int_str.startswith(b"0") and len(int_str) > 1)):
                raise BencodeError(f"Invalid bencoded integer: {int_str}")
            try:
                val = int(int_str)
            except ValueError:
                raise BencodeError(f"Cannot parse integer: {int_str}")
            return val, end + 1

        # List: l<contents>e
        elif char == b"l":
            cur = idx + 1
            res = []
            while cur < len(data) and data[cur:cur + 1] != b"e":
                val, cur = _decode_at(cur, depth + 1)
                res.append(val)
            if cur >= len(data) or data[cur:cur + 1] != b"e":
                raise BencodeError("Unterminated bencoded list.")
            return res, cur + 1

        # Dictionary: d<key><val>...e
        elif char == b"d":
            cur = idx + 1
            res = {}
            while cur < len(data) and data[cur:cur + 1] != b"e":
                # Key must be a byte string
                key, cur = _decode_at(cur, depth + 1)
                if not isinstance(key, (bytes, str)):
                    raise BencodeError("Bencode dictionary key must be a string.")
                # Decode key to str if valid utf-8, else leave as str representation
                key_str = key.decode("utf-8", errors="replace") if isinstance(key, bytes) else key
                val, cur = _decode_at(cur, depth + 1)
                res[key_str] = val
            if cur >= len(data) or data[cur:cur + 1] != b"e":
                raise BencodeError("Unterminated bencoded dictionary.")
            return res, cur + 1

        # Byte String: <length>:<bytes>
        elif char.isdigit():
            colon = data.find(b":", idx)
            if colon == -1:
                raise BencodeError("Unterminated bencoded string length.")
            len_str = data[idx:colon]
            try:
                length = int(len_str)
            except ValueError:
                raise BencodeError(f"Invalid string length in bencode: {len_str}")
            if length < 0:
                raise BencodeError("Negative string length in bencode.")
            if length > MAX_STRING_LENGTH:
                raise BencodeError(f"Bencode string length {length} exceeds maximum safety limit of {MAX_STRING_LENGTH} bytes.")
            start_str = colon + 1
            end_str = start_str + length
            if end_str > len(data):
                raise BencodeError(f"Bencoded string length {length} overflows input buffer.")
            return data[start_str:end_str], end_str

        else:
            raise BencodeError(f"Invalid bencode token at offset {idx}: {char!r}")

    result, consumed = _decode_at(0, 0)
    return result


def bencode_encode(val: Any) -> bytes:
    """Encodes Python structures into canonical bencoded byte sequences."""
    if isinstance(val, int):
        return f"i{val}e".encode("ascii")
    elif isinstance(val, (bytes, bytearray)):
        return f"{len(val)}:".encode("ascii") + bytes(val)
    elif isinstance(val, str):
        encoded = val.encode("utf-8")
        return f"{len(encoded)}:".encode("ascii") + encoded
    elif isinstance(val, (list, tuple)):
        parts = [b"l"]
        for item in val:
            parts.append(bencode_encode(item))
        parts.append(b"e")
        return b"".join(parts)
    elif isinstance(val, dict):
        parts = [b"d"]
        # In bencode, keys MUST be sorted lexicographically by raw byte values
        sorted_keys = sorted(val.keys(), key=lambda k: k.encode("utf-8") if isinstance(k, str) else bytes(k))
        for k in sorted_keys:
            parts.append(bencode_encode(k))
            parts.append(bencode_encode(val[k]))
        parts.append(b"e")
        return b"".join(parts)
    else:
        raise BencodeError(f"Cannot bencode object of type {type(val)}")


def parse_torrent_bytes(torrent_bytes: bytes) -> Dict[str, Any]:
    """
    Parses a raw .torrent file buffer into normalized metadata:
    - info_hash (40-char lowercase hex)
    - name
    - total_size
    - piece_count
    - piece_length
    - trackers (list of URLs)
    - is_multi_file (bool)
    - files: list of {index, path, size}
    - created_date (ISO or readable string)
    - comment
    """
    decoded = bencode_decode(torrent_bytes)
    if not isinstance(decoded, dict):
        raise BencodeError("Torrent file must be a bencoded dictionary.")

    info_dict = decoded.get("info")
    if not isinstance(info_dict, dict):
        raise BencodeError("Torrent file is missing required 'info' dictionary.")

    # Calculate SHA1 info_hash from the raw bencoded info dictionary
    raw_info = bencode_encode(info_dict)
    info_hash = hashlib.sha1(raw_info).hexdigest().lower()

    raw_name = info_dict.get("name", b"Unnamed_Torrent")
    if isinstance(raw_name, bytes):
        name = raw_name.decode("utf-8", errors="replace")
    else:
        name = str(raw_name)

    piece_length = int(info_dict.get("piece length", 0))
    pieces_raw = info_dict.get("pieces", b"")
    piece_count = len(pieces_raw) // 20 if isinstance(pieces_raw, (bytes, bytearray)) else 0

    files: List[Dict[str, Any]] = []
    total_size = 0
    is_multi_file = False

    if "files" in info_dict and isinstance(info_dict["files"], list):
        # Multi-file torrent
        is_multi_file = True
        for idx, f_entry in enumerate(info_dict["files"]):
            if not isinstance(f_entry, dict):
                continue
            f_size = int(f_entry.get("length", 0))
            path_parts = f_entry.get("path", [])
            clean_parts = []
            if isinstance(path_parts, list):
                for p in path_parts:
                    part_str = p.decode("utf-8", errors="replace") if isinstance(p, bytes) else str(p)
                    # Detect directory traversal or absolute path attempts
                    if part_str in ("..", ".", "") or "/" in part_str or "\\" in part_str:
                        raise ValidationError(f"Malicious path component detected in torrent file: {part_str}")
                    clean_parts.append(part_str)
            rel_path = "/".join(clean_parts) if clean_parts else f"file_{idx}"
            files.append({
                "index": idx,
                "path": rel_path,
                "size": f_size,
            })
            total_size += f_size
    else:
        # Single-file torrent
        is_multi_file = False
        f_size = int(info_dict.get("length", 0))
        total_size = f_size
        files.append({
            "index": 0,
            "path": name,
            "size": f_size,
        })

    # Trackers extraction
    trackers = []
    announce = decoded.get("announce")
    if announce:
        ann_str = announce.decode("utf-8", errors="replace") if isinstance(announce, bytes) else str(announce)
        if ann_str.strip():
            trackers.append(ann_str.strip())

    announce_list = decoded.get("announce-list")
    if isinstance(announce_list, list):
        for tier in announce_list:
            if isinstance(tier, list):
                for tr in tier:
                    tr_str = tr.decode("utf-8", errors="replace") if isinstance(tr, bytes) else str(tr)
                    if tr_str.strip() and tr_str.strip() not in trackers:
                        trackers.append(tr_str.strip())

    # Creation date
    creation_date = None
    raw_date = decoded.get("creation date")
    if raw_date and isinstance(raw_date, (int, float)):
        try:
            creation_date = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(raw_date))
        except Exception:
            pass

    # Comment
    comment = None
    raw_comment = decoded.get("comment")
    if raw_comment:
        comment = raw_comment.decode("utf-8", errors="replace") if isinstance(raw_comment, bytes) else str(raw_comment)

    return {
        "info_hash": info_hash,
        "name": name,
        "total_size": total_size,
        "piece_count": piece_count,
        "piece_length": piece_length,
        "trackers": trackers,
        "is_multi_file": is_multi_file,
        "files": files,
        "creation_date": creation_date,
        "comment": comment,
    }
