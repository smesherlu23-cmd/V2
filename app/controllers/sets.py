from __future__ import annotations

import threading
import time

import flet as ft

from ..core import layout as L
from ..core import queries
from ..core.text import plu_programs, plu_windows
from ..infra import log
from ..platform import windows as W
from ..ui import colors as C


class SetsController:
    def __init__(self, ui):
        self.ui = ui
        self.store = ui.store
        self.launcher = ui.launcher

    def launch_set(self, set_id, from_palette: bool = False):
        rec = self.store.get_set(set_id)
        if not rec:
            return
        if from_palette:
            self.ui.view.close_palette()
            self.ui.search_field.value = ""
        count = len(rec["items"])
        self.ui.toast.show(f"Открываю «{rec['name']}» · {count} {plu_programs(count)}",
                           icon=ft.Icons.LAYERS)
        self.ui.refresh()
        threading.Thread(target=lambda: self._run_set(rec, from_palette),
                         daemon=True).start()

    def _run_set(self, rec, from_palette: bool):
        delay = max(0.0, float(rec.get("delay_seconds") or 0.0))
        started, failed = [], 0
        try:
            for index, entry in enumerate(rec["items"]):
                app = self.store.get_app(entry["app_id"])
                if not app:
                    continue
                if index and delay:
                    time.sleep(delay)
                try:
                    res = self.launcher.launch(app)
                except Exception:
                    log.exception("launching %s from a set failed", app.get("path"))
                    res = {"ok": False}
                if res.get("ok"):
                    self.store.mark_launched(entry["app_id"])
                    started.append(app["name"])
                else:
                    failed += 1
            self.ui.running = set(self.launcher.running_ids())
            if not started:
                self.ui.toast.error(f"Ни одна программа из «{rec['name']}» не запустилась")
                self.ui._safe_refresh()
                return
            text = "Открыто: " + ", ".join(started)
            if failed:
                text += f" · не удалось: {failed}"
            self.ui.toast.show(text, icon=ft.Icons.LAYERS)
            if W.available() and queries.has_layout(rec):
                time.sleep(max(0.5, delay))
                self.arrange_set(rec["id"], quiet=True)
            self.ui._after_launch(from_palette)
        except Exception:
            log.exception("запуск набора «%s» failed", rec.get("name"))
            self.ui._safe_refresh()

    def arrange_set(self, set_id, quiet: bool = False):
        rec = self.store.get_set(set_id)
        if not rec:
            return
        if not W.available():
            if not quiet:
                self.ui.toast.error("Расставлять окна умеет только Windows-сборка")
            return
        area = W.work_area(rec["monitor"])
        fallback = False
        if area is None:
            area = W.work_area(0)
            fallback = rec["monitor"] != 0
        if area is None:
            if not quiet:
                self.ui.toast.error("Не удалось прочитать размеры экрана")
            return
        snapshot = W.list_windows()
        placed = 0
        conf = rec["layout"]
        for entry in rec["items"]:
            app = self.store.get_app(entry["app_id"])
            if not app:
                continue
            wins = W.windows_for(W.exe_names_for(app), snapshot)
            if not wins:
                continue
            if entry.get("minimized"):
                if W.minimize(wins[0]["hwnd"]):
                    placed += 1
                continue
            rect = L.rect_for(entry, conf["preset"], conf["split"], conf["vsplit"])
            if rect is None:
                continue
            if W.place(wins[0]["hwnd"], L.to_pixels(rect, area)):
                placed += 1
        if fallback:
            self.ui.toast.show(f"Монитора {rec['monitor'] + 1} нет — разложили на основном",
                               icon=ft.Icons.DESKTOP_WINDOWS, icon_color=C.MUTED)
        elif not quiet:
            self.ui.toast.show(f"Окна расставлены: {placed}" if placed
                               else "Ни одно окно набора не открыто",
                               icon=ft.Icons.CROP_FREE, icon_color=C.MUTED)
        self.ui._safe_refresh()

    def close_set_windows(self, set_id):
        rec = self.store.get_set(set_id)
        if not rec:
            return
        if not W.available():
            self.ui.toast.error("Закрывать окна умеет только Windows-сборка")
            return
        snapshot = W.list_windows()
        closed = 0
        for entry in rec["items"]:
            app = self.store.get_app(entry["app_id"])
            if not app:
                continue
            for win in W.windows_for(W.exe_names_for(app), snapshot):
                if W.close_window(win["hwnd"]):
                    closed += 1
        self.ui.toast.show(f"Закрыто окон: {closed}" if closed
                           else "Окон этого набора не нашлось",
                           icon=ft.Icons.CLOSE, icon_color=C.MUTED)
        self.ui._safe_refresh()

    def capture_set_layout(self, set_id):
        rec = self.store.get_set(set_id)
        if not rec:
            return
        if not W.available():
            self.ui.toast.error("Читать положение окон умеет только Windows-сборка")
            return
        area = W.work_area(rec["monitor"]) or W.work_area(0)
        if area is None:
            self.ui.toast.error("Не удалось прочитать размеры экрана")
            return
        before = [dict(i) for i in rec["items"]]
        snapshot = W.list_windows()
        items, rects = [], []
        for entry in rec["items"]:
            app = self.store.get_app(entry["app_id"])
            fresh = dict(entry)
            wins = W.windows_for(W.exe_names_for(app or {}), snapshot) if app else []
            if wins and not wins[0]["minimized"]:
                rect = L.to_fractions(wins[0]["rect"], area)
                fresh.update({"rect": list(rect), "slot": None, "minimized": False})
                rects.append(rect)
            elif wins:
                fresh.update({"rect": None, "slot": None, "minimized": True})
            items.append(fresh)
        if not rects:
            self.ui.toast.error("Ни одно окно набора не открыто")
            return
        preset, split, vsplit = L.nearest_preset(rects)
        self.store.update_set(set_id, {"items": items,
                                       "layout": {"preset": preset, "split": split,
                                                  "vsplit": vsplit}})
        self.ui.toast.show(f"Раскладка снята с {len(rects)} {plu_windows(len(rects))}",
                           icon=ft.Icons.SAVE, icon_color=C.MUTED,
                           action=lambda: self.restore_set_items(set_id, before,
                                                                 rec["layout"]),
                           action_label="Вернуть")
        self.ui.refresh()

    def restore_set_items(self, set_id, items, conf):
        self.store.update_set(set_id, {"items": items, "layout": conf})
        self.ui.refresh()

    def toggle_set_quick(self, set_id, value):
        self.store.update_set(set_id, {"quick": bool(value)})
        self.ui.refresh()

    def new_set(self):
        if self.ui.view.sel:
            self.make_set(list(self.ui.view.sel))
            return
        self.ui.toast.show("Выберите плитки — из них и собирается набор",
                           icon=ft.Icons.LAYERS, icon_color=C.MUTED,
                           action=self.ui._toggle_select_mode, action_label="Выбрать")

    def make_set(self, ids):
        apps = [a for a in self.ui.apps() if a["id"] in set(ids)]
        if len(apps) < 2:
            self.ui.toast.error("Для набора нужно хотя бы две программы")
            return
        rec = self.store.add_set(queries.set_name_for(apps), [a["id"] for a in apps])
        if not rec:
            return
        self.ui.view.clear_selection()
        self.ui.view.select_mode = False
        self.ui.view.open_set(rec["id"])
        self.ui.toast.show(f"Набор «{rec['name']}» собран", icon=ft.Icons.LAYERS,
                           icon_color=C.MUTED,
                           action=lambda: self.undo_set(rec["id"]), action_label="Вернуть")
        self.ui._on_library_changed()

    def add_to_set(self, set_id, app_ids):
        rec = self.store.get_set(set_id)
        if not rec:
            return
        before = list(rec["apps"])
        merged = before + [i for i in app_ids if i not in before]
        if merged == before:
            self.ui.toast.show(f"Уже в наборе «{rec['name']}»", icon=ft.Icons.LAYERS,
                               icon_color=C.MUTED)
            return
        self.store.update_set(set_id, {"apps": merged})
        self.ui.toast.show(f"Добавлено в «{rec['name']}»", icon=ft.Icons.LAYERS,
                           icon_color=C.MUTED,
                           action=lambda: self.restore_set_members(set_id, before),
                           action_label="Вернуть")
        self.ui.refresh()

    def remove_from_set(self, set_id, app_id):
        rec = self.store.get_set(set_id)
        if not rec:
            return
        before = [dict(i) for i in rec["items"]]
        rest = [i for i in rec["items"] if i["app_id"] != app_id]
        if len(rest) == len(before):
            return
        if not rest:
            self.remove_set(set_id)
            return
        self.store.update_set(set_id, {"items": rest})
        self.ui.toast.show("Убрано из набора", icon=ft.Icons.LAYERS, icon_color=C.MUTED,
                           action=lambda: self.restore_set_items(set_id, before,
                                                                 rec["layout"]),
                           action_label="Вернуть")
        self.ui.refresh()

    def restore_set_members(self, set_id, members):
        self.store.update_set(set_id, {"apps": members})
        self.ui.refresh()

    def undo_set(self, set_id):
        self.store.remove_set(set_id)
        self.ui.view.close_set()
        self.ui._on_library_changed()

    def remove_set(self, set_id):
        rec = self.store.remove_set(set_id)
        if not rec:
            return
        if self.ui.view.active_set == set_id:
            self.ui.view.close_set()
        self.ui.toast.show(f"Набор «{rec['name']}» удалён", icon=ft.Icons.DELETE_OUTLINE,
                           icon_color=C.MUTED,
                           action=lambda: self.restore_set(rec), action_label="Вернуть")
        self.ui._on_library_changed()

    def restore_set(self, rec):
        self.store.restore_set(rec)
        self.ui._on_library_changed()

    def rename_set(self, set_id, name):
        if (name or "").strip():
            self.store.update_set(set_id, {"name": name.strip()})
            self.ui._on_library_changed()

    def set_layout_preset(self, set_id, preset):
        self.store.update_set(set_id, {"layout": {"preset": preset}})
        self.ui.refresh()

    def set_layout_split(self, set_id, key, value):
        self.store.update_set(set_id, {"layout": {key: value}})
        self.ui.refresh()

    def set_set_delay(self, set_id, seconds):
        self.store.update_set(set_id, {"delay_seconds": seconds})
        self.ui.refresh()

    def set_set_monitor(self, set_id, index):
        self.store.update_set(set_id, {"monitor": index})
        self.ui.refresh()

    def set_close_together(self, set_id, value):
        self.store.update_set(set_id, {"close_together": bool(value)})
        self.ui.refresh()

    def set_item_slot(self, set_id, app_id, slot):
        self.store.update_set_item(set_id, app_id, {"slot": slot, "minimized": False})
        self.ui.refresh()

    def set_item_minimized(self, set_id, app_id, value):
        self.store.update_set_item(set_id, app_id, {"minimized": bool(value)})
        self.ui.refresh()

    def move_set_item(self, set_id, app_id, delta):
        self.store.move_set_item(set_id, app_id, delta)
        self.ui.refresh()
