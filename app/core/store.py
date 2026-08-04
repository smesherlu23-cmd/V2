from __future__ import annotations

import copy
import hashlib
import json
import os
import threading
import time
import uuid
from pathlib import Path

from . import layout as L
from ..infra import log
from ..infra.debounce import Debounce

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
    "onboarded": False,
    "collapsed": [],
}


def hue_from_string(text: str) -> int:
    digest = hashlib.md5(str(text).lower().encode("utf-8"), usedforsecurity=False).digest()
    return ((digest[0] << 8) | digest[1]) % 360


def _as_int(value, fallback: int = 0) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else fallback


def _clean_app(item, index: int) -> dict | None:
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
    rec["order"] = _as_int(rec.get("order"), index)
    rec["hidden"] = bool(rec.get("hidden"))
    for key in ("added_at", "last_launched", "launch_count"):
        rec[key] = _as_int(rec.get(key))
    hue = _as_int(rec.get("hue"), -1)
    rec["hue"] = hue if 0 <= hue < 360 else hue_from_string(rec["name"] or rec["path"])
    return rec


def _clean_category(item, index: int) -> dict | None:
    if not isinstance(item, dict):
        return None
    cat_id = item.get("id")
    if not isinstance(cat_id, str) or not cat_id.strip():
        return None
    rec = dict(item)
    rec["id"] = cat_id
    name = rec.get("name")
    rec["name"] = name.strip() if isinstance(name, str) and name.strip() else "Категория"
    rec["order"] = _as_int(rec.get("order"), index)
    rec["image"] = rec["image"] if isinstance(rec.get("image"), str) and rec["image"] else None
    return rec


def _clean_layout(raw) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    return {"preset": L.valid_preset(raw.get("preset")),
            "split": L.clamp(raw.get("split", L.DEFAULT_SPLIT), L.MIN_SPLIT, L.MAX_SPLIT),
            "vsplit": L.clamp(raw.get("vsplit", L.DEFAULT_VSPLIT), L.MIN_SPLIT, L.MAX_SPLIT)}


def _clean_item(raw, preset: str, index: int) -> dict | None:
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


def _clean_set(item, index: int) -> dict | None:
    if not isinstance(item, dict):
        return None
    set_id = item.get("id")
    if not isinstance(set_id, str) or not set_id.strip():
        return None
    rec = dict(item)
    rec["id"] = set_id
    name = rec.get("name")
    rec["name"] = name.strip() if isinstance(name, str) and name.strip() else "Набор"
    rec["order"] = _as_int(rec.get("order"), index)
    rec["quick"] = bool(rec.get("quick"))
    rec["layout"] = _clean_layout(rec.get("layout"))
    hotkey = rec.get("hotkey")
    rec["hotkey"] = hotkey.strip() if isinstance(hotkey, str) and hotkey.strip() else None
    rec["monitor"] = max(0, _as_int(rec.get("monitor")))
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
        entry = _clean_item(raw, preset, len(items))
        if entry is None or entry["app_id"] in seen:
            continue
        seen.add(entry["app_id"])
        items.append(entry)
    rec["items"] = items
    return _mirror_items(rec)


def _mirror_items(rec: dict) -> dict:
    rec["apps"] = [i["app_id"] for i in rec.get("items", [])]
    return rec


def _fit_slots(rec: dict) -> dict:
    count = L.slot_count(rec["layout"]["preset"])
    taken: set[int] = set()
    for entry in rec["items"]:
        slot = entry.get("slot")
        if not isinstance(slot, int) or slot >= count or slot in taken:
            entry["slot"] = None
        else:
            taken.add(slot)
    return rec


def _free_slot(rec: dict):
    count = L.slot_count(rec["layout"]["preset"])
    taken = {i.get("slot") for i in rec["items"] if isinstance(i.get("slot"), int)}
    return next((i for i in range(count) if i not in taken), None)


def _refill_slots(rec: dict) -> dict:
    for entry in rec["items"]:
        if entry.get("minimized") or entry.get("rect") or entry.get("slot") is not None:
            continue
        entry["slot"] = _free_slot(rec)
        if entry["slot"] is None:
            break
    return rec


def _clean_inbox(item, index: int) -> dict | None:
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
    rec["order"] = _as_int(rec.get("order"), index)
    rec["found_at"] = _as_int(rec.get("found_at"))
    return rec


def _clean_records(raw, clean) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for index, item in enumerate(raw if isinstance(raw, list) else []):
        rec = clean(item, index)
        if rec is None or rec["id"] in seen:
            continue
        seen.add(rec["id"])
        out.append(rec)
    return out


def _clean_settings(raw) -> dict:
    settings = dict(DEFAULT_SETTINGS)
    if isinstance(raw, dict):
        for key in DEFAULT_SETTINGS:
            if key in raw:
                settings[key] = raw[key]
    return settings


DATA_FILENAME = "centurio-data.json"
PERSIST_DEBOUNCE_DELAY = 1.5


def default_data_path() -> Path:
    base = Path(os.environ.get("APPDATA") or Path.home())
    return base / "Centurio" / DATA_FILENAME


class Store:
    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else default_data_path()
        self._lock = threading.RLock()
        self.on_error = None
        self.write_error: str | None = None
        self._persist_debounce = Debounce(PERSIST_DEBOUNCE_DELAY, self._debounced_persist)
        self.data = self._load()

    def _debounced_persist(self) -> None:
        with self._lock:
            self._persist()

    def _defaults(self) -> dict:
        return {
            "version": 3,
            "categories": copy.deepcopy(DEFAULT_CATEGORIES),
            "apps": [],
            "sets": [],
            "inbox": [],
            "settings": dict(DEFAULT_SETTINGS),
        }

    def _load(self) -> dict:
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                raw = fh.read()
        except FileNotFoundError:
            return self._defaults()
        except OSError:
            log.exception("не удалось прочитать файл данных: %s", self.path)
            return self._defaults()

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            log.exception("файл данных поврежден, помещение копии в карантин: %s", self.path)
            self._quarantine_corrupt(raw)
            return self._defaults()

        return self._sanitize(parsed)

    def _sanitize(self, parsed: dict) -> dict:
        cats = _clean_records(parsed.get("categories"), _clean_category)
        apps = _clean_records(parsed.get("apps"), _clean_app)
        known = {a["id"] for a in apps}
        sets = _clean_records(parsed.get("sets"), _clean_set)
        for rec in sets:
            rec["items"] = [i for i in rec["items"] if i["app_id"] in known]
            _fit_slots(_mirror_items(rec))
        have = {(a.get("path") or "").lower() for a in apps}
        inbox = [i for i in _clean_records(parsed.get("inbox"), _clean_inbox)
                 if i["path"].lower() not in have]
        return {
            "version": 3,
            "categories": cats or copy.deepcopy(DEFAULT_CATEGORIES),
            "apps": apps,
            "sets": [s for s in sets if s["items"]],
            "inbox": inbox,
            "settings": _clean_settings(parsed.get("settings")),
        }

    def _quarantine_corrupt(self, raw: str) -> None:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        dest = self.path.with_name(f"centurio-corrupt-{stamp}.json")
        try:
            dest.write_text(raw, encoding="utf-8")
        except OSError:
            log.exception("не удалось сохранить копию поврежденного файла данных: %s", dest)

    def _persist(self) -> bool:
        tmp = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_name(f"{self.path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self.data, fh, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        except (OSError, ValueError, TypeError) as exc:
            log.exception("не удалось сохранить файл данных: %s", self.path)
            self._discard_temp(tmp)
            self._report_write_error(str(exc))
            return False
        self.write_error = None
        return True

    def _discard_temp(self, tmp: Path | None) -> None:
        if tmp is None:
            return
        try:
            tmp.unlink()
        except OSError:
            pass

    def _report_write_error(self, message: str) -> None:
        first = self.write_error is None
        self.write_error = message
        if first and self.on_error:
            try:
                self.on_error(message)
            except Exception:
                log.exception("сбой в обратном вызове ошибки хранилища")

    def state(self) -> dict:
        with self._lock:
            return copy.deepcopy(self.data)

    def add_app(self, app: dict) -> dict:
        with self._lock:
            cats = self.data["categories"]
            record = {
                "id": str(uuid.uuid4()),
                "name": app.get("name") or "Без названия",
                "path": app.get("path") or "",
                "args": app.get("args") or [],
                "working_dir": app.get("working_dir") or "",
                "run_as_admin": bool(app.get("run_as_admin")),
                "sub": app.get("sub") or "",
                "category_id": app.get("category_id") or (cats[0]["id"] if cats else "work"),
                "hue": app["hue"] if isinstance(app.get("hue"), int) else hue_from_string(app.get("name") or app.get("path") or ""),
                "icon": app.get("icon") or None,
                "icon_fit": app.get("icon_fit") or "contain",
                "poster": app.get("poster") or None,
                "favorite": bool(app.get("favorite")),
                "quick": bool(app.get("quick")),
                "hidden": bool(app.get("hidden")),
                "hotkey": app.get("hotkey") or None,
                "track_exe": app.get("track_exe") or None,
                "order": app["order"] if isinstance(app.get("order"), int) else len(self.data["apps"]),
                "last_launched": 0,
                "launch_count": 0,
                "added_at": int(time.time() * 1000),
            }
            self.data["apps"].append(record)
            self._persist()
            return record

    def get_app(self, app_id: str) -> dict | None:
        with self._lock:
            return next((a for a in self.data["apps"] if a["id"] == app_id), None)

    def update_app(self, app_id: str, patch: dict, persist: bool = True) -> dict | None:
        with self._lock:
            app = self.get_app(app_id)
            if not app:
                return None
            for key in ("name", "path", "args", "working_dir", "run_as_admin", "sub", "category_id",
                        "hue", "icon", "icon_fit", "poster", "favorite", "quick", "hidden",
                        "hotkey", "track_exe", "order"):
                if key in patch:
                    app[key] = patch[key]
            if persist:
                self._persist()
            return app

    def update_apps(self, app_ids, patch: dict) -> int:
        with self._lock:
            touched = 0
            for app_id in dict.fromkeys(app_ids):
                if self.update_app(app_id, patch, persist=False) is not None:
                    touched += 1
            if touched:
                self._persist()
            return touched

    def reorder_apps(self, ordered_ids: list[str]) -> None:
        with self._lock:
            pos = {aid: i for i, aid in enumerate(ordered_ids)}
            for app in self.data["apps"]:
                if app["id"] in pos:
                    app["order"] = pos[app["id"]]
            self._persist()

    def remove_app(self, app_id: str) -> bool:
        return bool(self.remove_apps([app_id]))

    def remove_apps(self, app_ids) -> list[dict]:
        wanted = set(app_ids)
        with self._lock:
            gone = [a for a in self.data["apps"] if a["id"] in wanted]
            if not gone:
                return []
            self.data["apps"] = [a for a in self.data["apps"] if a["id"] not in wanted]
            for rec in self.data["sets"]:
                rec["items"] = [i for i in rec["items"] if i["app_id"] not in wanted]
                _mirror_items(rec)
            self.data["sets"] = [s for s in self.data["sets"] if s["items"]]
            self._persist()
            return copy.deepcopy(gone)

    def restore_apps(self, records) -> int:
        with self._lock:
            have = {a["id"] for a in self.data["apps"]}
            fresh = [copy.deepcopy(r) for r in records
                     if isinstance(r, dict) and r.get("id") and r["id"] not in have]
            if not fresh:
                return 0
            self.data["apps"] += fresh
            self._persist()
            return len(fresh)

    def mark_launched(self, app_id: str) -> dict | None:
        with self._lock:
            app = self.get_app(app_id)
            if not app:
                return None
            app["last_launched"] = int(time.time() * 1000)
            app["launch_count"] = app.get("launch_count", 0) + 1
            self._persist()
            return app

    def add_category(self, name: str, icon: str | None = None, color: str | None = None) -> dict:
        with self._lock:
            cat = {"id": str(uuid.uuid4()), "name": name or "Категория",
                   "icon": icon or None, "color": color or "#ffffff", "image": None,
                   "order": len(self.data["categories"])}
            self.data["categories"].append(cat)
            self._persist()
            return cat

    def update_category(self, cat_id: str, patch: dict) -> dict | None:
        with self._lock:
            cat = next((c for c in self.data["categories"] if c["id"] == cat_id), None)
            if not cat:
                return None
            for key in ("name", "icon", "color", "order", "image"):
                if key in patch:
                    cat[key] = patch[key]
            self._persist()
            return cat

    def reorder_categories(self, ordered_ids: list[str]) -> None:
        with self._lock:
            pos = {cid: i for i, cid in enumerate(ordered_ids)}
            for cat in self.data["categories"]:
                if cat["id"] in pos:
                    cat["order"] = pos[cat["id"]]
            self._persist()

    def move_category(self, cat_id: str, delta: int) -> None:
        with self._lock:
            cats = sorted(self.data["categories"], key=lambda c: c.get("order", 0))
            ids = [c["id"] for c in cats]
            if cat_id not in ids:
                return
            i = ids.index(cat_id)
            j = max(0, min(len(ids) - 1, i + delta))
            if i == j:
                return
            ids.insert(j, ids.pop(i))
            self.reorder_categories(ids)

    def remove_category(self, cat_id: str) -> dict | None:
        with self._lock:
            cat = next((c for c in self.data["categories"] if c["id"] == cat_id), None)
            if cat is None:
                return None
            self.data["categories"] = [c for c in self.data["categories"] if c["id"] != cat_id]
            fallback = self.data["categories"][0]["id"] if self.data["categories"] else None
            moved = []
            for app in self.data["apps"]:
                if app.get("category_id") == cat_id:
                    app["category_id"] = fallback
                    moved.append(app["id"])
            self._persist()
            return {"category": copy.deepcopy(cat), "apps": moved}

    def restore_category(self, undo: dict) -> bool:
        if not isinstance(undo, dict) or not isinstance(undo.get("category"), dict):
            return False
        cat = undo["category"]
        if not cat.get("id"):
            return False
        with self._lock:
            if any(c["id"] == cat["id"] for c in self.data["categories"]):
                return False
            self.data["categories"].append(copy.deepcopy(cat))
            self.data["categories"].sort(key=lambda c: c.get("order", 0))
            back = set(undo.get("apps") or [])
            for app in self.data["apps"]:
                if app["id"] in back:
                    app["category_id"] = cat["id"]
            self._persist()
            return True

    def add_set(self, name: str, app_ids, quick: bool = True) -> dict | None:
        with self._lock:
            known = {a["id"] for a in self.data["apps"]}
            members = [aid for aid in dict.fromkeys(app_ids) if aid in known]
            if not members:
                return None
            rec = _clean_set({"id": str(uuid.uuid4()),
                              "name": (name or "").strip() or "Набор",
                              "items": [{"app_id": aid} for aid in members],
                              "quick": bool(quick), "order": len(self.data["sets"])},
                             len(self.data["sets"]))
            self.data["sets"].append(rec)
            self._persist()
            return copy.deepcopy(rec)

    def get_set(self, set_id: str) -> dict | None:
        with self._lock:
            found = next((s for s in self.data["sets"] if s["id"] == set_id), None)
            return copy.deepcopy(found) if found else None

    def update_set(self, set_id: str, patch: dict) -> dict | None:
        with self._lock:
            rec = next((s for s in self.data["sets"] if s["id"] == set_id), None)
            if not rec:
                return None
            known = {a["id"] for a in self.data["apps"]}
            if "name" in patch:
                rec["name"] = (patch["name"] or "").strip() or rec["name"]
            if "quick" in patch:
                rec["quick"] = bool(patch["quick"])
            if "hotkey" in patch:
                hk = (patch["hotkey"] or "").strip() if isinstance(patch["hotkey"], str) else ""
                rec["hotkey"] = hk or None
            if "monitor" in patch:
                rec["monitor"] = max(0, _as_int(patch["monitor"]))
            if "close_together" in patch:
                rec["close_together"] = bool(patch["close_together"])
            if "delay_seconds" in patch:
                try:
                    rec["delay_seconds"] = max(0.0, min(MAX_SET_DELAY,
                                                        float(patch["delay_seconds"])))
                except (TypeError, ValueError):
                    pass
            preset_changed = False
            if "layout" in patch:
                merged = dict(rec["layout"])
                merged.update(patch["layout"] if isinstance(patch["layout"], dict) else {})
                before = rec["layout"]["preset"]
                rec["layout"] = _clean_layout(merged)
                preset_changed = rec["layout"]["preset"] != before
            if "items" in patch:
                raw = patch["items"] if isinstance(patch["items"], list) else []
                items = []
                for entry in raw:
                    clean = _clean_item(entry, rec["layout"]["preset"], len(items))
                    if clean and clean["app_id"] in known:
                        items.append(clean)
                rec["items"] = items
            if "apps" in patch:
                wanted = [aid for aid in dict.fromkeys(patch["apps"] or []) if aid in known]
                by_id = {i["app_id"]: i for i in rec["items"]}
                rec["items"] = [by_id[aid] for aid in wanted if aid in by_id]
                for aid in wanted:
                    if aid in by_id:
                        continue
                    rec["items"].append({"app_id": aid, "slot": _free_slot(rec),
                                         "minimized": False, "rect": None})
            _fit_slots(_mirror_items(rec))
            if preset_changed:
                _refill_slots(rec)
            self._persist()
            return copy.deepcopy(rec)

    def update_set_item(self, set_id: str, app_id: str, patch: dict) -> dict | None:
        with self._lock:
            rec = next((s for s in self.data["sets"] if s["id"] == set_id), None)
            if not rec:
                return None
            entry = next((i for i in rec["items"] if i["app_id"] == app_id), None)
            if entry is None:
                return None
            if "slot" in patch:
                slot = patch["slot"]
                count = L.slot_count(rec["layout"]["preset"])
                entry["slot"] = slot if isinstance(slot, int) and 0 <= slot < count else None
                if entry["slot"] is not None:
                    for other in rec["items"]:
                        if other is not entry and other.get("slot") == entry["slot"]:
                            other["slot"] = None
                    entry["rect"] = None
            if "minimized" in patch:
                entry["minimized"] = bool(patch["minimized"])
                if entry["minimized"]:
                    entry["slot"] = None
                    entry["rect"] = None
            if "rect" in patch:
                rect = L.normal_rect(patch["rect"])
                entry["rect"] = list(rect) if rect else None
            self._persist()
            return copy.deepcopy(rec)

    def reorder_set_items(self, set_id: str, ordered_ids) -> dict | None:
        with self._lock:
            rec = next((s for s in self.data["sets"] if s["id"] == set_id), None)
            if not rec:
                return None
            by_id = {i["app_id"]: i for i in rec["items"]}
            order = [aid for aid in dict.fromkeys(ordered_ids) if aid in by_id]
            rec["items"] = ([by_id[aid] for aid in order]
                            + [i for i in rec["items"] if i["app_id"] not in set(order)])
            _mirror_items(rec)
            self._persist()
            return copy.deepcopy(rec)

    def move_set_item(self, set_id: str, app_id: str, delta: int) -> dict | None:
        with self._lock:
            rec = next((s for s in self.data["sets"] if s["id"] == set_id), None)
            if not rec:
                return None
            ids = [i["app_id"] for i in rec["items"]]
            if app_id not in ids:
                return None
            i = ids.index(app_id)
            j = max(0, min(len(ids) - 1, i + delta))
            if i == j:
                return copy.deepcopy(rec)
            rec["items"].insert(j, rec["items"].pop(i))
            _mirror_items(rec)
            self._persist()
            return copy.deepcopy(rec)

    def reorder_sets(self, ordered_ids: list[str]) -> None:
        with self._lock:
            pos = {sid: i for i, sid in enumerate(ordered_ids)}
            for rec in self.data["sets"]:
                if rec["id"] in pos:
                    rec["order"] = pos[rec["id"]]
            self._persist()

    def remove_set(self, set_id: str) -> dict | None:
        with self._lock:
            rec = next((s for s in self.data["sets"] if s["id"] == set_id), None)
            if not rec:
                return None
            self.data["sets"] = [s for s in self.data["sets"] if s["id"] != set_id]
            self._persist()
            return copy.deepcopy(rec)

    def restore_set(self, record: dict) -> bool:
        if not isinstance(record, dict) or not record.get("id"):
            return False
        with self._lock:
            if any(s["id"] == record["id"] for s in self.data["sets"]):
                return False
            rec = _clean_set(copy.deepcopy(record), len(self.data["sets"]))
            if rec is None:
                return False
            known = {a["id"] for a in self.data["apps"]}
            rec["items"] = [i for i in rec["items"] if i["app_id"] in known]
            if not rec["items"]:
                return False
            self.data["sets"].append(_mirror_items(rec))
            self.data["sets"].sort(key=lambda s: s.get("order", 0))
            self._persist()
            return True

    def queue_inbox(self, items) -> int:
        with self._lock:
            have = {(a.get("path") or "").lower() for a in self.data["apps"]}
            have |= {i["path"].lower() for i in self.data["inbox"]}
            added = 0
            for item in items:
                path = (item.get("path") or "").strip()
                if not path or path.lower() in have:
                    continue
                have.add(path.lower())
                self.data["inbox"].append({
                    "id": str(uuid.uuid4()),
                    "name": item.get("name") or "Без названия",
                    "path": path,
                    "icon": item.get("icon"),
                    "icon_fit": item.get("icon_fit") or "contain",
                    "poster": item.get("poster"),
                    "sub": item.get("sub") or "",
                    "track_exe": item.get("track_exe"),
                    "source": item.get("source") or "",
                    "found_at": int(time.time() * 1000),
                    "order": len(self.data["inbox"]),
                })
                added += 1
            if added:
                self._persist()
            return added

    def take_inbox(self, item_id: str) -> dict | None:
        with self._lock:
            item = next((i for i in self.data["inbox"] if i["id"] == item_id), None)
            if item is None:
                return None
            self.data["inbox"] = [i for i in self.data["inbox"] if i["id"] != item_id]
            self._persist()
            return copy.deepcopy(item)

    def restore_inbox(self, item: dict) -> bool:
        if not isinstance(item, dict) or not item.get("id"):
            return False
        with self._lock:
            if any(i["id"] == item["id"] for i in self.data["inbox"]):
                return False
            self.data["inbox"].append(copy.deepcopy(item))
            self.data["inbox"].sort(key=lambda i: i.get("order", 0))
            self._persist()
            return True

    def clear_inbox(self) -> list[dict]:
        with self._lock:
            gone = copy.deepcopy(self.data["inbox"])
            if gone:
                self.data["inbox"] = []
                self._persist()
            return gone

    def set_setting(self, key: str, value, persist: bool | str = True) -> dict:
        with self._lock:
            if key in DEFAULT_SETTINGS:
                self.data["settings"][key] = value
                if persist == "debounce":
                    self._persist_debounce.schedule()
                elif persist:
                    self._persist()
            return dict(self.data["settings"])

    def flush(self) -> bool:
        with self._lock:
            self._persist_debounce.cancel()
            return self._persist()

    def export_data(self, dest: str | Path) -> Path:
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            with open(dest, "w", encoding="utf-8") as fh:
                json.dump(self.data, fh, ensure_ascii=False, indent=2)
        return dest

    def backup(self) -> Path:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        return self.export_data(self.path.with_name(f"centurio-backup-{stamp}.json"))

    def import_data(self, src: str | Path, merge: bool = False) -> bool:
        try:
            with open(src, "r", encoding="utf-8") as fh:
                incoming = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return False
        if not isinstance(incoming, dict) or "apps" not in incoming:
            return False
        clean = self._sanitize(incoming)
        with self._lock:
            if merge:
                have = {a["id"] for a in self.data["apps"] if a.get("id")}
                self.data["apps"] += [a for a in clean["apps"] if a.get("id") not in have]
                hc = {c["id"] for c in self.data["categories"] if c.get("id")}
                self.data["categories"] += [c for c in clean["categories"] if c.get("id") not in hc]
            else:
                self.data = clean
            self._persist()
        return True
