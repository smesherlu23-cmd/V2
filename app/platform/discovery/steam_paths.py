from __future__ import annotations

import glob
import json
import os
import re
import threading

from ...infra import log
from . import steam_art

_STEAM_SKIP_ID = {"228980"}

_STEAM_SKIP_NAME = ("steamworks common", "proton", "steam linux runtime", "steamvr media")

_STEAM_EXE_JUNK = ("unins", "uninstall", "vcredist", "vc_redist", "dxsetup", "dxwebsetup",
                   "directx", "redist", "crashhandler", "crashreport", "launcher", "setup",
                   "cleanup", "touchup", "dotnet", "oalinst", "notification_helper",
                   "prereq", "activation", "diagnostic", "helper", "reporter")

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

def _steam_exe_remember(icon_cache: str | None, appid: str, root: str, exe: str) -> None:
    path = _steam_exe_cache_path(icon_cache)
    if not path or not exe:
        return
    with _exe_cache_lock:
        data = _steam_exe_cache_read(icon_cache)
        data[str(appid)] = {"exe": exe, "root": root}
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
    if not installdir:
        return None
    root = os.path.join(lib, "steamapps", "common", installdir)
    if not os.path.isdir(root):
        return None
    if appid:
        cached = _steam_exe_cached(icon_cache, appid, root)
        if cached:
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
            try:
                size = os.path.getsize(os.path.join(dirpath, fn))
            except OSError:
                continue
            candidates.append((size, fn, low))
        if seen > 20000:
            break
    if not candidates:
        return None
    tokens = [t for t in re.split(r"[^a-z0-9]+", name.lower()) if len(t) >= 3]
    found = None
    for _size, fn, low in sorted(candidates, key=lambda c: -c[0]):
        if any(t in low for t in tokens):
            found = fn
            break
    if found is None:
        found = max(candidates, key=lambda c: c[0])[1]
    if appid and found:
        _steam_exe_remember(icon_cache, appid, root, found)
    return found

def steam_exe_for(path: str, icon_cache: str | None = None) -> str | None:
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
            exe = _steam_game_exe(lib, _vdf_val(text, "installdir"),
                                  _vdf_val(text, "name") or "", icon_cache, appid)
            if exe:
                return exe
    return None

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
                icon, fit = steam_art._steam_icon(root, appid, icon_cache)
                poster = steam_art._steam_portrait(root, appid, icon_cache)
                track = (_steam_game_exe(lib, _vdf_val(text, "installdir"), name,
                                         icon_cache, appid)
                         if os.name == "nt" else None)
                games.append({"name": name, "path": f"steam://rungameid/{appid}",
                              "icon": icon, "icon_fit": fit, "source": "steam",
                              "sub": "Steam", "track_exe": track, "poster": poster})
    return games
