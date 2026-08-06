"""Reads Epic Games Launcher manifests to list installed games."""

from __future__ import annotations

import glob
import json
import os

from . import windows


def _epic_games(icon_cache: str | None) -> list[dict]:
    if os.name != "nt":
        return []
    mani = os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"),
                        "Epic", "EpicGamesLauncher", "Data", "Manifests")
    if not os.path.isdir(mani):
        return []
    games = []
    for f in glob.glob(os.path.join(mani, "*.item")):
        try:
            with open(f, encoding="utf-8", errors="ignore") as fh:
                d = json.load(fh)
        except Exception:
            continue
        name = d.get("DisplayName")
        if not name or d.get("bIsIncompleteInstall"):
            continue
        app_name = d.get("MainGameAppName") or d.get("AppName")
        path = None
        if app_name:
            path = (f"com.epicgames.launcher://apps/{app_name}"
                    "?action=launch&silent=true")
        else:
            loc, exe = d.get("InstallLocation"), d.get("LaunchExecutable")
            if loc and exe:
                path = os.path.join(loc, exe)
        if not path:
            continue
        icon = None
        loc, exe = d.get("InstallLocation"), d.get("LaunchExecutable")
        track = os.path.basename(exe) if exe else None
        if icon_cache and loc and exe:
            full = os.path.join(loc, exe)
            if os.path.exists(full):
                icon = windows._win_extract_one(full, icon_cache)
        games.append({"name": name, "path": path, "icon": icon,
                      "icon_fit": "contain", "source": "epic", "sub": "Epic Games",
                      "track_exe": track})
    return games
