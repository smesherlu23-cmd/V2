"""Resolves and extracts an icon for a given app path (Windows .exe
or Steam appid), plus the backfill pass that fills in icons/art
for apps added before this schema existed, and cache pruning for
files nothing references anymore."""

from __future__ import annotations

import os
import re
import time

from ...infra import log
from . import steam_art, steam_paths, windows


def extract_icon(path: str, icon_cache: str | None) -> str | None:
    if not path or not icon_cache:
        return None
    try:
        if os.name == "nt" and path.lower().endswith(".exe") and os.path.exists(path):
            return windows._win_extract_one(path, icon_cache)
    except Exception:
        log.exception("extract_icon failed for %s", path)
    return None

def resolve_icon_for(path: str, icon_cache: str | None = None) -> tuple[str | None, str]:
    if not path:
        return None, "contain"
    m = re.match(r"steam://rungameid/(\d+)", path)
    if m:
        appid = m.group(1)
        for root in steam_paths._steam_roots():
            icon, fit = steam_art._steam_icon(root, appid, icon_cache)
            if icon:
                return icon, fit
        dl = steam_art._steam_cdn_art(appid, icon_cache)
        return (dl, "cover") if dl else (None, "contain")
    if path.lower().startswith("shell:appsfolder\\"):
        try:
            if os.name == "nt":
                return windows._win_extract_store_one(path, icon_cache), "contain"
        except Exception:
            log.exception("resolve_icon_for (Store) failed for %s", path)
        return None, "contain"
    try:
        if os.name == "nt" and path.lower().endswith(".exe") and os.path.exists(path):
            return windows._win_extract_one(path, icon_cache), "contain"
    except Exception:
        log.exception("resolve_icon_for failed for %s", path)
    return None, "contain"

PRUNE_MIN_AGE_DAYS = 14.0

def _norm_path(value) -> str:
    if not isinstance(value, str) or not value:
        return ""
    try:
        return os.path.normcase(os.path.abspath(value))
    except (OSError, ValueError):
        return ""

def prune_icon_cache(store, icon_cache: str | None = None,
                     min_age_days: float = PRUNE_MIN_AGE_DAYS) -> int:
    if not icon_cache or not os.path.isdir(icon_cache):
        return 0
    state = store.state()
    keep = {_norm_path(steam_paths._steam_exe_cache_path(icon_cache))}
    for records, fields in ((state.get("apps") or [], ("icon", "poster")),
                            (state.get("inbox") or [], ("icon", "poster")),
                            (state.get("categories") or [], ("image",))):
        for rec in records:
            if not isinstance(rec, dict):
                continue
            for field in fields:
                keep.add(_norm_path(rec.get(field)))
    keep.discard("")

    cutoff = time.time() - max(0.0, min_age_days) * 86400
    removed = 0
    for root, _dirs, files in os.walk(icon_cache):
        for name in files:
            full = os.path.join(root, name)
            if _norm_path(full) in keep:
                continue
            try:
                if os.path.getmtime(full) > cutoff:
                    continue
                os.unlink(full)
            except OSError:
                continue
            removed += 1
    if removed:
        log.info("кэш иконок: удалено осиротевших файлов: %d", removed)
    return removed

ICON_SCHEMA = 7

def backfill_icons(store, icon_cache: str | None = None, refresh: bool = False) -> bool:
    changed = False
    for app in list(store.state().get("apps", [])):
        patch = {}
        path = app.get("path") or ""
        if refresh or not app.get("icon"):
            icon, fit = resolve_icon_for(path, icon_cache)
            if icon and (icon != app.get("icon") or fit != app.get("icon_fit")):
                patch["icon"] = icon
                patch["icon_fit"] = fit
        if not (app.get("sub") or "").strip():
            if path.startswith("steam://"):
                patch["sub"] = "Steam"
            elif path.startswith("com.epicgames.launcher://"):
                patch["sub"] = "Epic Games"
        if path.startswith("steam://") and not (app.get("track_exe") or "").strip():
            exe = steam_paths.steam_exe_for(path, icon_cache)
            if exe:
                patch["track_exe"] = exe
        if path.startswith("steam://") and (refresh or not app.get("poster")):
            poster = steam_art.poster_for(path, icon_cache)
            if poster and poster != app.get("poster"):
                patch["poster"] = poster
        if patch:
            store.update_app(app["id"], patch, persist=False)
            changed = True
    if changed:
        store.flush()
    return changed
