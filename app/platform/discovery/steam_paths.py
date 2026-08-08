from __future__ import annotations

import glob
import json
import os
import re
import threading

from ...infra import log
from . import steam_art, windows

_STEAM_SKIP_ID = {"228980"}

_STEAM_SKIP_NAME = ("steamworks common", "proton", "steam linux runtime", "steamvr media")

_STEAM_EXE_JUNK = ("unins", "uninstall", "vcredist", "vc_redist", "dxsetup", "dxwebsetup",
                   "directx", "redist", "crashhandler", "crashreport", "launcher", "setup",
                   "cleanup", "touchup", "dotnet", "oalinst", "notification_helper",
                   "prereq", "activation", "diagnostic", "helper", "reporter")

# Тот же список, но без "launcher": для track_exe маленький лаунчер — то,
# от чего нужно избавиться (игра к моменту проверки уже запущена и это
# не он), а вот для иконки — наоборот, чаще всего именно у него приличная
# иконка, а не у движкового бинарника, который track_exe специально ищет.
_STEAM_ICON_EXE_JUNK = tuple(j for j in _STEAM_EXE_JUNK if j != "launcher") + (
    "dedicated", "server", "eac", "battleye", "easyanticheat", "anticheat")

_STEAM_EXE_CACHE_NAME = "steam-exe.json"

_exe_cache_lock = threading.Lock()

def _steam_exe_cache_path(icon_cache: str | None) -> str | None:
    return os.path.join(icon_cache, _STEAM_EXE_CACHE_NAME) if icon_cache else None

def _steam_exe_cache_read(icon_cache: str | None) -> dict:
    path = _steam_exe_cache_path(icon_cache)
    if not path:
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}

def _steam_exe_cached(icon_cache: str | None, appid: str, root: str) -> str | None:
    """Возвращает полный путь к exe, найденный и запомненный в прошлый раз."""
    with _exe_cache_lock:
        entry = _steam_exe_cache_read(icon_cache).get(str(appid))
    if not isinstance(entry, dict):
        return None
    exe = entry.get("exe")
    if not isinstance(exe, str) or not exe:
        return None
    if entry.get("root") != root:
        return None
    return exe

def _steam_exe_remember(icon_cache: str | None, appid: str, root: str, exe_full: str) -> None:
    path = _steam_exe_cache_path(icon_cache)
    if not path or not exe_full:
        return
    with _exe_cache_lock:
        data = _steam_exe_cache_read(icon_cache)
        data[str(appid)] = {"exe": exe_full, "root": root}
        try:
            os.makedirs(icon_cache, exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False)
        except OSError:
            log.exception("не удалось сохранить кэш путей Steam: %s", path)

def reset_steam_exe_cache(icon_cache: str | None) -> None:
    path = _steam_exe_cache_path(icon_cache)
    if not path:
        return
    with _exe_cache_lock:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass
        except OSError:
            log.exception("не удалось очистить кэш путей Steam: %s", path)

def _steam_game_exe(lib: str, installdir: str | None, name: str,
                    icon_cache: str | None = None, appid: str | None = None) -> str | None:
    """The game's own executable, just the filename — this is what track_exe
    matches running windows against, so a bare name is what callers want."""
    full = _steam_game_exe_full(lib, installdir, name, icon_cache, appid)
    return os.path.basename(full) if full else None

def _steam_game_exe_full(lib: str, installdir: str | None, name: str,
                         icon_cache: str | None = None,
                         appid: str | None = None) -> str | None:
    """Same lookup as _steam_game_exe, but the full path — needed to actually
    open the file (extracting its icon), not just match a process name."""
    if not installdir:
        return None
    root = os.path.join(lib, "steamapps", "common", installdir)
    if not os.path.isdir(root):
        return None
    if appid:
        cached = _steam_exe_cached(icon_cache, appid, root)
        if cached and os.path.exists(cached):
            return cached
    candidates: list[tuple[int, str, str]] = []
    seen = 0
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            if not fn.lower().endswith(".exe"):
                continue
            seen += 1
            if seen > 20000:
                break
            low = fn.lower()
            if any(j in low for j in _STEAM_EXE_JUNK):
                continue
            full_path = os.path.join(dirpath, fn)
            try:
                size = os.path.getsize(full_path)
            except OSError:
                continue
            candidates.append((size, full_path, low))
        if seen > 20000:
            break
    if not candidates:
        return None
    tokens = [t for t in re.split(r"[^a-z0-9]+", name.lower()) if len(t) >= 3]
    found = None
    for _size, full_path, low in sorted(candidates, key=lambda c: -c[0]):
        if any(t in low for t in tokens):
            found = full_path
            break
    if found is None:
        found = max(candidates, key=lambda c: c[0])[1]
    if appid and found:
        _steam_exe_remember(icon_cache, appid, root, found)
    return found

def _steam_game_icon_exe(lib: str, installdir: str | None, name: str) -> str | None:
    """Which exe to pull this game's icon from — a different pick than
    _steam_game_exe_full/track_exe on purpose. track_exe wants whatever
    process is actually running once the game is up, which tends to be the
    big "-Shipping"/engine binary, however deep it sits — and that binary's
    icon is usually just the generic engine one. The properly branded icon
    is far more often on a small stub sitting right at the install root, so
    here shallow and small wins over deep and big instead."""
    if not installdir:
        return None
    root = os.path.join(lib, "steamapps", "common", installdir)
    if not os.path.isdir(root):
        return None
    candidates: list[tuple[int, int, str, str]] = []
    seen = 0
    for dirpath, _dirs, files in os.walk(root):
        depth = os.path.relpath(dirpath, root).count(os.sep)
        for fn in files:
            if not fn.lower().endswith(".exe"):
                continue
            seen += 1
            if seen > 20000:
                break
            low = fn.lower()
            if any(j in low for j in _STEAM_ICON_EXE_JUNK):
                continue
            full_path = os.path.join(dirpath, fn)
            try:
                size = os.path.getsize(full_path)
            except OSError:
                continue
            candidates.append((depth, size, full_path, low))
        if seen > 20000:
            break
    if not candidates:
        return None
    tokens = [t for t in re.split(r"[^a-z0-9]+", name.lower()) if len(t) >= 3]
    named = [c for c in candidates if any(t in c[3] for t in tokens)]
    pool = named or candidates
    pool.sort(key=lambda c: (c[0], c[1]))
    return pool[0][2]

def _for_each_steam_manifest(path: str, cb):
    """Finds the manifest for this steam:// path across every library and
    runs cb(lib, installdir, name, appid) against it, returning the first
    truthy result — the shared plumbing behind steam_exe_for() and
    steam_icon_exe_for(), which only differ in which exe they want."""
    m = re.match(r"steam://rungameid/(\d+)", path or "")
    if not m or os.name != "nt":
        return None
    appid = m.group(1)
    for root in _steam_roots():
        for lib in _steam_libraries(root):
            acf = os.path.join(lib, "steamapps", f"appmanifest_{appid}.acf")
            try:
                with open(acf, encoding="utf-8", errors="ignore") as fh:
                    text = fh.read()
            except OSError:
                continue
            result = cb(lib, _vdf_val(text, "installdir"), _vdf_val(text, "name") or "", appid)
            if result:
                return result
    return None

def steam_exe_for(path: str, icon_cache: str | None = None) -> str | None:
    """The game's own executable, just the filename — for matching running
    windows against track_exe."""
    return _for_each_steam_manifest(
        path, lambda lib, installdir, name, appid:
            _steam_game_exe(lib, installdir, name, icon_cache, appid))

def steam_icon_exe_for(path: str) -> str | None:
    """Full path to the exe most likely to carry this game's real icon —
    for when Steam hasn't cached a small icon of its own for it."""
    return _for_each_steam_manifest(
        path, lambda lib, installdir, name, appid: _steam_game_icon_exe(lib, installdir, name))

def _steam_roots() -> list[str]:
    roots = []
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
                p, _ = winreg.QueryValueEx(k, "SteamPath")
                if p:
                    roots.append(p)
        except Exception:
            log.exception("не удалось прочитать путь к Steam из реестра")
        roots += [r"C:\Program Files (x86)\Steam", r"C:\Program Files\Steam"]
    return [r for r in dict.fromkeys(roots) if r and os.path.isdir(r)]

def _steam_libraries(root: str) -> list[str]:
    libs = [root]
    vdf = os.path.join(root, "steamapps", "libraryfolders.vdf")
    try:
        with open(vdf, encoding="utf-8", errors="ignore") as fh:
            text = fh.read()
        for m in re.finditer(r'"path"\s*"([^"]+)"', text):
            libs.append(m.group(1).replace("\\\\", "\\"))
    except OSError:
        pass
    return list(dict.fromkeys(libs))

def _vdf_val(text: str, key: str) -> str | None:
    m = re.search(rf'"{re.escape(key)}"\s*"([^"]*)"', text, re.IGNORECASE)
    return m.group(1) if m else None

def _extract_exe_icon(exe_full: str, icon_cache: str) -> str | None:
    try:
        return windows._win_extract_one(exe_full, icon_cache)
    except Exception:
        log.exception("не удалось вытащить иконку из %s", exe_full)
        return None

def _steam_games(icon_cache: str | None) -> list[dict]:
    games = []
    seen = set()
    for root in _steam_roots():
        for lib in _steam_libraries(root):
            for acf in glob.glob(os.path.join(lib, "steamapps", "appmanifest_*.acf")):
                try:
                    with open(acf, encoding="utf-8", errors="ignore") as fh:
                        text = fh.read()
                except OSError:
                    continue
                appid = _vdf_val(text, "appid")
                name = _vdf_val(text, "name")
                if not appid or not name or appid in _STEAM_SKIP_ID or appid in seen:
                    continue
                if any(s in name.lower() for s in _STEAM_SKIP_NAME):
                    continue
                seen.add(appid)
                installdir = _vdf_val(text, "installdir")
                icon, fit = steam_art._steam_icon(root, appid, icon_cache)
                poster = steam_art._steam_portrait(root, appid, icon_cache)
                track = (_steam_game_exe(lib, installdir, name, icon_cache, appid)
                         if os.name == "nt" else None)
                if not icon and os.name == "nt" and icon_cache:
                    # Steam не закэшировал свою маленькую иконку для этой игры —
                    # вытаскиваем настоящую иконку прямо из её exe, как для
                    # обычных программ, а не остаёмся с пустым местом.
                    icon_exe = _steam_game_icon_exe(lib, installdir, name)
                    if icon_exe:
                        icon = _extract_exe_icon(icon_exe, icon_cache)
                        fit = "contain"
                games.append({"name": name, "path": f"steam://rungameid/{appid}",
                              "icon": icon, "icon_fit": fit, "source": "steam",
                              "sub": "Steam", "track_exe": track, "poster": poster})
    return games
