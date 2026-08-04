from __future__ import annotations

import os
import threading
import time
from pathlib import Path

from ..core import queries
from ..core.text import plu_apps
from ..infra import log
from ..platform import discovery

DISCOVERY_TTL = 120.0


class ScanController:

    def __init__(self, ui):
        self.ui = ui
        self.store = ui.store
        self.notify = ui.notify
        self._discovered = None
        self._discovered_at = 0.0
        self._scanning = False
        self._scan_errors: list[dict] = []
        self._scan_lock = threading.Lock()
        self._manual_found: list[dict] = []

    def cached_discovery(self):
        if self._discovered is None:
            return None
        if time.monotonic() - self._discovered_at > DISCOVERY_TTL:
            return None
        return self._discovered

    def _remember_discovery(self, found):
        self._discovered = found
        self._discovered_at = time.monotonic()

    def scanning(self) -> bool:
        with self._scan_lock:
            return self._scanning

    def scan_errors(self) -> list[dict]:
        with self._scan_lock:
            return list(self._scan_errors)

    def start_scan(self, force: bool = False):
        with self._scan_lock:
            if self._scanning:
                return
            if not force and self.cached_discovery() is not None:
                return
            self._scanning = True
            self._scan_errors = []

        def work():
            report = {}
            try:
                if force:
                    discovery.reset_cdn_state()
                    discovery.reset_steam_exe_cache(self.ui.icon_cache_dir())
                found = discovery.discover_apps(self.ui.icon_cache_dir(), report=report)
                self._remember_discovery(found)
                errors = report.get("errors") or []
            except Exception as exc:
                log.exception("не удалось выполнить проверку установленных программ")
                errors = [{"source": "", "label": "Поиск программ", "error": str(exc)}]
            with self._scan_lock:
                self._scanning = False
                self._scan_errors = errors
            self.ui.safe_refresh()

        threading.Thread(target=work, daemon=True).start()

    def dismiss_scan_errors(self):
        with self._scan_lock:
            self._scan_errors = []
        self.ui.refresh()

    def found_groups(self):
        found = self.cached_discovery() or []
        found = list(found) + list(self._manual_found)
        existing = {(a.get("path") or "").lower() for a in self.ui.apps()}
        return queries.group_found(found, existing, self.ui.categories(),
                                   only_new=self.ui.view.only_new,
                                   query=self.ui.view.add_query)

    def toggle_only_new(self):
        self.ui.view.only_new = not self.ui.view.only_new
        self.ui.refresh()

    def set_add_query(self, text):
        self.ui.view.add_query = text or ""
        self.ui.refresh()

    def set_manual_path(self, text):
        self.ui.view.manual_path = text or ""

    def add_manual_path(self, text=None):
        raw = (text if text is not None else self.ui.view.manual_path or "").strip().strip('"')
        if not raw:
            self.notify.error("Вставьте путь к программе")
            return
        if not os.path.isfile(raw):
            self.notify.error("Файл не найден", detail=raw)
            return
        name = Path(raw).stem.replace("-", " ").replace("_", " ").strip()
        item = {"name": (name[:1].upper() + name[1:]) if name else "Программа",
                "path": raw, "source": "manual",
                "icon": discovery.extract_icon(raw, self.ui.icon_cache_dir())}
        found = list(self._manual_found)
        if any((f.get("path") or "").lower() == raw.lower() for f in found):
            self.notify.show("Этот путь уже в списке", icon="check_circle", tone="muted")
            return
        found.append(item)
        self._manual_found = found
        self.ui.view.manual_path = ""
        self.ui.view.add_sel.add(raw.lower())
        self.notify.show(f"{item['name']} добавлен в список", icon="link", tone="muted")
        self.ui.refresh()

    def toggle_add_row(self, row):
        if not row["is_new"]:
            self.notify.show(f"{row['name']} уже в библиотеке", icon="check_circle", tone="muted")
            return
        self.ui.view.toggle_add(row["key"])
        self.ui.refresh()

    def toggle_add_group(self, group):
        keys = [r["key"] for r in group["rows"] if r["is_new"]]
        checked = all(k in self.ui.view.add_sel for k in keys) if keys else False
        self.ui.view.set_add_group(keys, not checked)
        self.ui.refresh()

    def cycle_add_category(self, row):
        cats = self.ui.categories()
        if len(cats) < 2:
            return
        ids = [c["id"] for c in cats]
        current = self.ui.view.add_cat.get(row["key"], row["cat"])
        index = ids.index(current) if current in ids else -1
        self.ui.view.add_cat[row["key"]] = ids[(index + 1) % len(ids)]
        self.ui.refresh()

    def add_category_for(self, row) -> str | None:
        return self.ui.view.add_cat.get(row["key"], row["cat"])

    def _chosen_add_rows(self):
        rows = {r["key"]: r for g in self.found_groups() for r in g["rows"]}
        return [rows[k] for k in self.ui.view.add_sel if k in rows and rows[k]["is_new"]]

    def commit_add(self):
        chosen = self._chosen_add_rows()
        if not chosen:
            self.notify.show("Отметьте хотя бы одну программу", icon="check_circle", tone="muted")
            return
        added = []
        for row in chosen:
            item = row["item"]
            added.append(self.store.add_app({
                "name": item.get("name"), "path": item.get("path"), "icon": item.get("icon"),
                "icon_fit": item.get("icon_fit"), "sub": item.get("sub", ""),
                "track_exe": item.get("track_exe"), "poster": item.get("poster"),
                "category_id": self.add_category_for(row),
            }))
        self.ui.view.reset_add()
        self._manual_found = []
        self.ui.view.set_screen("grid")
        self.ui.view.filter = "all"
        self.notify.show(f"Добавлено {len(added)} {plu_apps(len(added))}",
                           action=lambda: self._restore_added(added), action_label="Вернуть")
        self.ui.on_library_changed()
        self.backfill_icons_async()

    def defer_add(self):
        chosen = self._chosen_add_rows()
        if not chosen:
            self.notify.show("Отметьте, что отложить", icon="inbox", tone="muted")
            return
        queued = self.store.queue_inbox([r["item"] for r in chosen])
        self.ui.view.reset_add()
        self.ui.view.set_screen("grid")
        self.notify.show(f"В разборе: {queued}", icon="inbox", tone="muted",
                           action=self.ui.open_triage, action_label="Разобрать")
        self.ui.on_library_changed()

    def _restore_added(self, records):
        self.store.remove_apps([r["id"] for r in records])
        self.ui.on_library_changed()

    def pick_file(self):
        self.ui.ask_for_file("Выберите программу", self.file_picked)

    def file_picked(self, path):
        if not path:
            return
        target = self.ui.relocating
        if target:
            self.ui.relocating = None
            self.store.update_app(target, {"path": path, "icon": None, "poster": None})
            self.notify.show("Путь обновлён", icon="check")
            self.ui.on_library_changed()
            self.backfill_icons_async()
            return
        if self.ui.view.screen == "add":
            self.add_manual_path(path)
            return
        base = Path(path).stem.replace("-", " ").replace("_", " ").strip()
        name = (base[:1].upper() + base[1:]) if base else "Программа"
        item = {"name": name, "path": path, "source": "manual"}
        cat_id = queries.suggest_category(item, self.ui.categories())
        cat = next((c for c in self.ui.categories() if c["id"] == cat_id), None)
        icon = discovery.extract_icon(path, self.ui.icon_cache_dir()) if path else None
        record = self.store.add_app({"name": name, "path": path, "icon": icon,
                                     "category_id": cat_id})
        self.ui.view.select_one(record["id"])
        self.notify.show(f"{name} добавлен в «{cat['name']}»" if cat else f"{name} добавлен",
                           icon="magic", tone="muted",
                           action=lambda: self._cycle_category(record["id"]),
                           action_label="Другая")
        self.ui.on_library_changed()

    def _cycle_category(self, app_id):
        cats = self.ui.categories()
        if len(cats) < 2:
            return
        app = self.store.get_app(app_id)
        ids = [c["id"] for c in cats]
        current = app.get("category_id") if app else None
        index = ids.index(current) if current in ids else -1
        nxt = cats[(index + 1) % len(cats)]
        self.store.update_app(app_id, {"category_id": nxt["id"]})
        self.notify.show(f"Теперь в «{nxt['name']}»", icon="folder", tone="muted")
        self.ui.refresh()

    def backfill_icons_async(self):
        def work():
            try:
                if discovery.backfill_icons(self.store, self.ui.icon_cache_dir()):
                    self.ui.on_library_changed()
            except Exception:
                log.exception("не удалось повторно разрешить иконки после добавления")
        threading.Thread(target=work, daemon=True).start()

    def rescan(self, silent: bool = False):
        if not silent:
            self.notify.show("Смотрю, что установлено", icon="search", tone="muted")

        def work():
            try:
                cache = self.ui.icon_cache_dir()
                if not silent:
                    discovery.reset_cdn_state()
                    discovery.reset_steam_exe_cache(cache)
                changed = discovery.backfill_icons(self.store, cache, refresh=not silent)
                found = discovery.discover_apps(cache)
                self._remember_discovery(found)
                try:
                    discovery.prune_icon_cache(self.store, cache)
                except Exception:
                    log.exception("не удалось прибрать кэш иконок")
                existing = {(a.get("path") or "").lower() for a in self.store.state()["apps"]}
                new = [a for a in found if (a.get("path") or "").lower() not in existing]
                if new and self.store.state()["settings"].get("triage", True):
                    queued = self.store.queue_inbox(new)
                    self.ui.on_library_changed()
                    if queued:
                        word = "новая программа ждёт" if queued == 1 else "новые программы ждут"
                        self.notify.show(f"{queued} {word} в разборе", icon="inbox", tone="good", action=self.ui.open_triage,
                                          action_label="Разобрать")
                    return
                self.ui.on_library_changed()
                if new:
                    self.notify.show(f"Нашлось нового: {len(new)}", icon="search", tone="muted", action=self.ui.open_add,
                                       action_label="Показать")
                elif not silent:
                    self.notify.show("Иконки обновлены" if changed else "Всё актуально")
            except Exception:
                log.exception("не удалось пересканировать")
                if not silent:
                    self.notify.error("Не удалось пересканировать",
                                        action=lambda: self.rescan(), action_label="Повторить")
        threading.Thread(target=work, daemon=True).start()
