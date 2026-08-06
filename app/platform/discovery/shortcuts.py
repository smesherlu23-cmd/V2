"""Reads Desktop and Startup shortcut names, used to rank freshly
discovered programs by how likely the user actually cares about
them during onboarding."""

from __future__ import annotations

import os
import re

from ...infra import log

_SHORTCUT_EXT = (".lnk", ".url")

def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9а-яё]+", "", (name or "").lower())

def _shortcut_names(directory: str) -> set[str]:
    out: set[str] = set()
    try:
        entries = os.listdir(directory)
    except OSError:
        return out
    for entry in entries:
        stem, ext = os.path.splitext(entry)
        if ext.lower() in _SHORTCUT_EXT:
            norm = _norm(stem)
            if norm:
                out.add(norm)
    return out

def desktop_names() -> set[str]:
    home = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    names: set[str] = set()
    for folder in ("Desktop", "Рабочий стол"):
        names |= _shortcut_names(os.path.join(home, folder))
    public = os.environ.get("PUBLIC")
    if public:
        names |= _shortcut_names(os.path.join(public, "Desktop"))
    return names

def autostart_names() -> set[str]:
    names: set[str] = set()
    appdata = os.environ.get("APPDATA")
    if appdata:
        names |= _shortcut_names(os.path.join(
            appdata, r"Microsoft\Windows\Start Menu\Programs\Startup"))
    if os.name != "nt":
        return names
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
            for i in range(winreg.QueryInfoKey(key)[1]):
                value_name = winreg.EnumValue(key, i)[0]
                norm = _norm(value_name)
                if norm:
                    names.add(norm)
    except OSError:
        pass
    except Exception:
        log.exception("не удалось прочитать ключ запуска для получения предложений по первому запуску")
    return names

def suggest_first_run(found: list[dict], limit: int = 8) -> list[dict]:
    try:
        startup, desktop = autostart_names(), desktop_names()
    except Exception:
        log.exception("не удалось собрать подсказки при первом запуске")
        startup, desktop = set(), set()

    tiers: list[list[dict]] = [[], [], []]
    for item in found:
        norm = _norm(item.get("name"))
        if not norm:
            continue
        if norm in startup:
            tiers[0].append({"app": item, "hint": "в автозагрузке"})
        elif norm in desktop:
            tiers[1].append({"app": item, "hint": "на рабочем столе"})
        elif item.get("source") == "startmenu":
            tiers[2].append({"app": item, "hint": "в меню «Пуск»"})

    out: list[dict] = []
    for tier in tiers:
        for suggestion in tier:
            if len(out) >= limit:
                return out
            out.append(suggestion)
    return out
