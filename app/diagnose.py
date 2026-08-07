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


def _matches(name, path, needle):
    n = needle.lower()
    return n in (name or "").lower() or n in (path or "").lower()


def run(search: str | None = None) -> None:
    print("диагностика")
    print(f"Python: {platform.python_version()} ({sys.executable})")
    print(f"платформа: {platform.system()} {platform.release()} ({os.name})")
    print(f"процесс: {'64-bit' if sys.maxsize > 2**32 else '32-bit'} "
          f"(sys.maxsize={sys.maxsize})")
    print("Зависимости:")
    for m in ("flet", "pystray", "PIL", "pynput", "psutil"):
        print(f"  {m:10}: {_mod(m)}")

    from app.core.store import default_data_path
    print(f"путь: {default_data_path()}")
    icon_cache = str(default_data_path().parent / "icons")

    from app.platform import discovery
    if os.name == "nt":
        exe = discovery._powershell_exe()
        print(f"powershell: {exe}"
              + (" (через Sysnative — обходит перенаправление реестра для 32-битного "
                 "процесса)" if "sysnative" in exe.lower() else ""))

        t0 = time.time()
        raw, stderr, code = discovery.raw_windows_entries(icon_cache)
        dt = time.time() - t0
        print(f"PowerShell (Меню «Пуск» + реестр + Store): {len(raw)} записей "
              f"за {dt:.1f}s, код={code}")
        if stderr:
            print(f"  stderr: {stderr[:2000]}")

        by_src = {}
        for x in raw:
            by_src[x.get("src", "?")] = by_src.get(x.get("src", "?"), 0) + 1
        print(f"  по источникам: {by_src}")

        dropped = [x for x in raw
                  if x.get("name") and x.get("path")
                  and discovery._is_windows_system(x["name"], x["path"])]
        print(f"  из них отфильтровано как системные/мусор: {len(dropped)}")

        store_raw = [x for x in raw if x.get("src") == "store"]
        store_with_icon = [x for x in store_raw if x.get("icon")]
        print(f"  Store-приложений найдено: {len(store_raw)}, "
              f"с иконкой: {len(store_with_icon)}")
        for x in store_raw[:10]:
            mark = "🖼" if x.get("icon") else "· нет иконки"
            print(f"    {mark} {x.get('name', '')[:40]}")

        if search:
            print(f"\n  поиск «{search}» в сыром выводе PowerShell (до фильтрации):")
            hits = [x for x in raw if _matches(x.get("name"), x.get("path"), search)]
            if hits:
                for x in hits:
                    junk = discovery._is_windows_system(x.get("name", ""), x.get("path", ""))
                    print(f"    НАЙДЕН [{x.get('src')}] {x.get('name')} — "
                          f"{x.get('path')}" + ("  (отфильтрован как мусор!)" if junk else ""))
            else:
                print(f"    НЕ НАЙДЕН вообще — PowerShell не увидел «{search}» "
                      "ни в меню «Пуск», ни в реестре, ни в Store. "
                      "Проблема на уровне поиска, не фильтра.")

    t0 = time.time()
    apps = discovery.discover_apps(icon_cache)
    dt = time.time() - t0
    games = [a for a in apps if a.get("source") in ("steam", "epic")]
    with_icon = [a for a in apps if a.get("icon")]
    print(f"\nитого найдено {len(apps)} записей за {dt:.1f}s "
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
    run(search=sys.argv[1] if len(sys.argv) > 1 else None)
