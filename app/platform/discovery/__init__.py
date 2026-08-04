from __future__ import annotations

import os

from ...infra import log
from . import steam_art, steam_paths, windows  # noqa: F401
from .epic import _epic_games
from .icons import (  # noqa: F401
    ICON_SCHEMA,
    _norm_path,
    backfill_icons,
    extract_icon,
    prune_icon_cache,
    resolve_icon_for,
)
from .shortcuts import autostart_names, desktop_names, suggest_first_run  # noqa: F401
from .steam_art import (  # noqa: F401
    _CDN_MAX_FAILURES,
    _cdn_available,
    _cdn_record,
    _steam_cdn_art,
    _steam_portrait,
    poster_for,
    reset_cdn_state,
)
from .steam_paths import (  # noqa: F401
    _STEAM_SKIP_ID,
    _steam_game_exe,
    _steam_games,
    _steam_roots,
    _vdf_val,
    reset_steam_exe_cache,
    steam_exe_for,
)
from .windows import (  # noqa: F401
    _WIN_ICON_ONE_PS,
    _WIN_PS,
    _discover_windows,
    _is_windows_system,
    _looks_like_junk,
)

__all__ = [
    "ICON_SCHEMA",
    "_steam_roots",
    "autostart_names",
    "backfill_icons",
    "desktop_names",
    "discover_apps",
    "extract_icon",
    "poster_for",
    "prune_icon_cache",
    "reset_cdn_state",
    "reset_steam_exe_cache",
    "resolve_icon_for",
    "steam_exe_for",
    "suggest_first_run",
]


def discover_apps(icon_cache: str | None = None, on_progress=None,
                  report: dict | None = None) -> list[dict]:
    if icon_cache:
        try:
            os.makedirs(icon_cache, exist_ok=True)
        except OSError:
            icon_cache = None

    steps = []
    if os.name == "nt":
        steps.append(("windows", "Меню «Пуск» и реестр", _discover_windows))
    steps += [("steam", "Steam", _steam_games), ("epic", "Epic Games", _epic_games)]

    apps: list[dict] = []
    errors = []
    for index, (key, label, fn) in enumerate(steps):
        if on_progress:
            try:
                on_progress(label, index, len(steps))
            except Exception:
                log.exception("не удалось выполнить обратный вызов хода проверки")
        try:
            apps += fn(icon_cache)
        except Exception as exc:
            log.exception("%s обнаружение не удалось", key)
            errors.append({"source": key, "label": label, "error": str(exc)})
    if on_progress:
        try:
            on_progress("", len(steps), len(steps))
        except Exception:
            log.exception("не удалось выполнить обратный вызов хода проверки")
    if report is not None:
        report["errors"] = errors
    return _dedupe(apps)


def _dedupe(apps: list[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    for a in apps:
        path = (a.get("path") or "").strip()
        name = (a.get("name") or "").strip()
        if not path or not name:
            continue
        key = path.lower()
        if key not in seen:
            seen[key] = {"name": name, "path": path, "icon": a.get("icon"),
                         "icon_fit": a.get("icon_fit", "contain"), "source": a.get("source", ""),
                         "sub": a.get("sub", ""), "track_exe": a.get("track_exe"),
                         "poster": a.get("poster")}
        elif not seen[key].get("source") and a.get("source"):
            seen[key]["source"] = a["source"]
        elif not seen[key].get("icon") and a.get("icon"):
            seen[key]["icon"] = a.get("icon")
            seen[key]["icon_fit"] = a.get("icon_fit", "contain")
    return sorted(seen.values(), key=lambda x: x["name"].lower())
