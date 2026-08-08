from __future__ import annotations

import hashlib

from .. import layout as L

DEFAULT_CATEGORIES = [
    {"id": "work", "name": "Работа", "icon": "work", "color": "#ffffff", "order": 0},
    {"id": "create", "name": "Творчество", "icon": "brush", "color": "#ffffff", "order": 1},
    {"id": "games", "name": "Игры", "icon": "sports_esports", "color": "#ffffff", "order": 2},
    {"id": "dev", "name": "Разработка", "icon": "code", "color": "#ffffff", "order": 3},
]

DEFAULT_LAUNCH_HOTKEY = "Ctrl+Space"
DEFAULT_SET_DELAY = 2.0
MAX_SET_DELAY = 30.0

DEFAULT_SETTINGS = {
    "autostart": False,
    "minimize_to_tray": True,
    "close_to_tray": True,
    "accent": "#f5f5f7",
    "tile_size": "large",
    "rail_size": "normal",
    "show_quick_row": True,
    "game_posters": True,
    "auto_rescan": False,
    "view_filter": "all",
    "view_sort": "alpha",
    "view_mode": "grid",
    "win_w": None,
    "win_h": None,
    "win_x": None,
    "win_y": None,
    "win_max": False,
    "icon_schema": 0,
    "launch_hotkey": DEFAULT_LAUNCH_HOTKEY,
    "hide_after": True,
    "triage": True,
    "calm": False,
    "hints": True,
    "debug_log": False,
    "collapsed": [],
}


def hue_from_string(text: str) -> int:
    digest = hashlib.md5(str(text).lower().encode("utf-8"), usedforsecurity=False).digest()
    return ((digest[0] << 8) | digest[1]) % 360


def as_int(value, fallback: int = 0) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else fallback


def clean_app(item, index: int) -> dict | None:
    if not isinstance(item, dict):
        return None
    app_id = item.get("id")
    if not isinstance(app_id, str) or not app_id.strip():
        return None
    rec = dict(item)
    rec["id"] = app_id
    name = rec.get("name")
    rec["name"] = name.strip() if isinstance(name, str) and name.strip() else "Без названия"
    rec["path"] = rec["path"] if isinstance(rec.get("path"), str) else ""
    rec["order"] = as_int(rec.get("order"), index)
    rec["hidden"] = bool(rec.get("hidden"))
    for key in ("added_at", "last_launched", "launch_count"):
        rec[key] = as_int(rec.get(key))
    hue = as_int(rec.get("hue"), -1)
    rec["hue"] = hue if 0 <= hue < 360 else hue_from_string(rec["name"] or rec["path"])
    return rec


def clean_category(item, index: int) -> dict | None:
    if not isinstance(item, dict):
        return None
    cat_id = item.get("id")
    if not isinstance(cat_id, str) or not cat_id.strip():
        return None
    rec = dict(item)
    rec["id"] = cat_id
    name = rec.get("name")
    rec["name"] = name.strip() if isinstance(name, str) and name.strip() else "Категория"
    rec["order"] = as_int(rec.get("order"), index)
    rec["image"] = rec["image"] if isinstance(rec.get("image"), str) and rec["image"] else None
    return rec


def clean_layout(raw) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    return {"preset": L.valid_preset(raw.get("preset")),
            "split": L.clamp(raw.get("split", L.DEFAULT_SPLIT), L.MIN_SPLIT, L.MAX_SPLIT),
            "vsplit": L.clamp(raw.get("vsplit", L.DEFAULT_VSPLIT), L.MIN_SPLIT, L.MAX_SPLIT)}


def clean_item(raw, preset: str, index: int) -> dict | None:
    if isinstance(raw, str):
        raw = {"app_id": raw}
    if not isinstance(raw, dict):
        return None
    app_id = raw.get("app_id")
    if not isinstance(app_id, str) or not app_id:
        return None
    count = L.slot_count(preset)
    if "slot" in raw:
        slot = raw["slot"]
        if not isinstance(slot, int) or isinstance(slot, bool) or not 0 <= slot < count:
            slot = None
    else:
        slot = index if index < count else None
    return {"app_id": app_id, "slot": slot, "minimized": bool(raw.get("minimized")),
            "rect": list(L.normal_rect(raw.get("rect")) or []) or None}


def clean_set(item, index: int) -> dict | None:
    if not isinstance(item, dict):
        return None
    set_id = item.get("id")
    if not isinstance(set_id, str) or not set_id.strip():
        return None
    rec = dict(item)
    rec["id"] = set_id
    name = rec.get("name")
    rec["name"] = name.strip() if isinstance(name, str) and name.strip() else "Набор"
    rec["order"] = as_int(rec.get("order"), index)
    rec["quick"] = bool(rec.get("quick"))
    rec["layout"] = clean_layout(rec.get("layout"))
    hotkey = rec.get("hotkey")
    rec["hotkey"] = hotkey.strip() if isinstance(hotkey, str) and hotkey.strip() else None
    rec["monitor"] = max(0, as_int(rec.get("monitor")))
    rec["close_together"] = bool(rec.get("close_together"))
    delay = rec.get("delay_seconds", DEFAULT_SET_DELAY)
    try:
        rec["delay_seconds"] = max(0.0, min(MAX_SET_DELAY, float(delay)))
    except (TypeError, ValueError):
        rec["delay_seconds"] = DEFAULT_SET_DELAY

    raw_items = rec.get("items")
    if not isinstance(raw_items, list):
        raw_items = rec.get("apps") if isinstance(rec.get("apps"), list) else []
    preset = rec["layout"]["preset"]
    items: list[dict] = []
    seen: set[str] = set()
    for raw in raw_items:
        entry = clean_item(raw, preset, len(items))
        if entry is None or entry["app_id"] in seen:
            continue
        seen.add(entry["app_id"])
        items.append(entry)
    rec["items"] = items
    return mirror_items(rec)


def mirror_items(rec: dict) -> dict:
    rec["apps"] = [i["app_id"] for i in rec.get("items", [])]
    return rec


def fit_slots(rec: dict) -> dict:
    count = L.slot_count(rec["layout"]["preset"])
    taken: set[int] = set()
    for entry in rec["items"]:
        slot = entry.get("slot")
        if not isinstance(slot, int) or slot >= count or slot in taken:
            entry["slot"] = None
        else:
            taken.add(slot)
    return rec


def free_slot(rec: dict):
    count = L.slot_count(rec["layout"]["preset"])
    taken = {i.get("slot") for i in rec["items"] if isinstance(i.get("slot"), int)}
    return next((i for i in range(count) if i not in taken), None)


def refill_slots(rec: dict) -> dict:
    for entry in rec["items"]:
        if entry.get("minimized") or entry.get("rect") or entry.get("slot") is not None:
            continue
        entry["slot"] = free_slot(rec)
        if entry["slot"] is None:
            break
    return rec


def clean_inbox(item, index: int) -> dict | None:
    if not isinstance(item, dict):
        return None
    path = item.get("path")
    if not isinstance(path, str) or not path.strip():
        return None
    rec = dict(item)
    rec["id"] = item["id"] if isinstance(item.get("id"), str) and item["id"] else path.lower()
    rec["path"] = path.strip()
    name = rec.get("name")
    rec["name"] = name.strip() if isinstance(name, str) and name.strip() else "Без названия"
    rec["source"] = rec["source"] if isinstance(rec.get("source"), str) else ""
    rec["order"] = as_int(rec.get("order"), index)
    rec["found_at"] = as_int(rec.get("found_at"))
    return rec


def clean_records(raw, clean) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for index, item in enumerate(raw if isinstance(raw, list) else []):
        rec = clean(item, index)
        if rec is None or rec["id"] in seen:
            continue
        seen.add(rec["id"])
        out.append(rec)
    return out


_BOOL_SETTINGS = {
    "autostart", "minimize_to_tray", "close_to_tray", "show_quick_row",
    "game_posters", "auto_rescan", "win_max", "hide_after", "triage",
    "calm", "hints", "debug_log",
}

_STR_SETTINGS = {"accent", "tile_size", "rail_size", "view_filter", "view_sort",
                 "view_mode", "launch_hotkey"}

_INT_OR_NONE_SETTINGS = {"win_w", "win_h", "win_x", "win_y"}


def _clean_setting_value(key: str, value, default):
    if key in _BOOL_SETTINGS:
        return value if isinstance(value, bool) else default
    if key in _STR_SETTINGS:
        return value if isinstance(value, str) and value.strip() else default
    if key in _INT_OR_NONE_SETTINGS:
        if value is None:
            return None
        return value if isinstance(value, int) and not isinstance(value, bool) else default
    if key == "icon_schema":
        return value if isinstance(value, int) and not isinstance(value, bool) else default
    if key == "collapsed":
        return [c for c in value if isinstance(c, str)] if isinstance(value, list) else default
    return value


def clean_settings(raw) -> dict:
    settings = dict(DEFAULT_SETTINGS)
    if isinstance(raw, dict):
        for key, default in DEFAULT_SETTINGS.items():
            if key in raw:
                settings[key] = _clean_setting_value(key, raw[key], default)
    return settings
