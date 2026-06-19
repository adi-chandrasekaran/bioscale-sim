from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Optional

CACHE_DIR = Path(__file__).resolve().parents[2] / "cache"
DEFAULT_TTL_SECONDS = 60 * 60 * 24  # 24 hours


def _cache_path(key: str) -> Path:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{digest}.json"


def get_cached(key: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> Optional[Any]:
    path = _cache_path(key)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if time.time() - payload.get("cached_at", 0) > ttl_seconds:
            return None
        return payload.get("data")
    except (json.JSONDecodeError, OSError):
        return None


def set_cached(key: str, data: Any) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(key)
    payload = {"cached_at": time.time(), "data": data}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
