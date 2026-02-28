import hashlib
import json


def stable_hash(obj: dict) -> str:
    """Produce a deterministic SHA-256 hash of a JSON-serializable dict."""
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def file_hash(content: bytes) -> str:
    """SHA-256 hash of raw file bytes."""
    return hashlib.sha256(content).hexdigest()
