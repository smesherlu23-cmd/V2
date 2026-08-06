from __future__ import annotations

import threading
import time

_lock = threading.Lock()
_snapshot: dict[int, str] = {}
_at = 0.0
TTL = 2.0


def snapshot(max_age: float = TTL) -> dict[int, str]:
    """The pid->lowercased-name map, refreshed at most every `max_age` seconds.

    Returns a copy: this is a module-level cache shared by every caller in
    the process (the process monitor thread and any window-matching code
    running alongside it), and handing out the live dict would let one
    caller's mutation corrupt what everyone else reads.
    """
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
