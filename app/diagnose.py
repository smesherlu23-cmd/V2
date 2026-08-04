from __future__ import annotations

import os
import platform
import sys
import time
from pathlib import Path


def _mod(name):
    try:
        __import__(name)
        return "OK"
    except Exception as exc:
        return f"MISSING ({exc.__class__.__name__})"


def run() -> None:
    print("диагностика")
    print(f"Python: {platform.python_version()} ({sys.executable})")
    print(f"платформа: {platform.system()} {platform.release()} ({os.name})")
    print("Зависимости:")
    for m in ("flet", "pystray", "PIL", "pynput", "psutil"):
        print(f"  {m:10}: {_mod(m)}")

    from app.core.store import default_data_path
    print(f"путь: {default_data_path()}")
    icon_cache = str(default_data_path().parent / "icons")

    from app.platform import discovery
    t0 = time.time()
    apps = discovery.discover_apps(icon_cache)
    dt = time.time() - t0
    games = [a for a in apps if a.get("source") in ("steam", "epic")]
    with_icon = [a for a in apps if a.get("icon")]
    print(f"найдено {len(apps)} записей за {dt:.1f}s "
          f"({len(games)} игр, {len(with_icon)} с иконками)")
    print("ВЫБОРКА 20")
    for a in apps[:20]:
        icon = "🖼" if a.get("icon") else "·"
        print(f"  [{a.get('source',''):8}] {icon} {a['name'][:40]:40} {a.get('path','')[:60]}")

    for r in discovery._steam_roots():
        print(f"  {r}")
    if not discovery._steam_roots():
        print("  не найдено корневых папок Steam")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    run()
