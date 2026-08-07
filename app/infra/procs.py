from __future__ import annotations

import threading
import time

_lock = threading.Lock()
_snapshot: dict[int, str] = {}
_at = 0.0
TTL = 2.0


def snapshot(max_age: float = TTL) -> dict[int, str]:
    global _snapshot, _at
    now = time.monotonic()
    with _lock:
        if now - _at <= max_age:
            return dict(_snapshot)
    try:
        import psutil
    except Exception:
        return {}
    fresh: dict[int, str] = {}
    try:
        for proc in psutil.process_iter(["pid", "name"]):
            name = proc.info.get("name")
            if name:
                fresh[proc.info["pid"]] = name.lower()
    except Exception:
        return {}
    with _lock:
        _snapshot = fresh
        _at = now
    return dict(fresh)
