from __future__ import annotations

import flet as ft

from ..core import layout as L
from ..core import queries
from ..platform import windows as W
from . import menus


class ContextMenus:
    def __init__(self, ui):
        self.ui = ui

    def menu_at(self, e):
        if e is None:
            return self.ui._window_width() / 2, 180.0
        return float(getattr(e, "global_x", 0) or 0), float(getattr(e, "global_y", 0) or 0)

    def on_menu_dismissed(self):
        self.ui.safe_refresh()

    def app_menu(self, app, e):
        app = self.ui.store.get_app(app["id"]) or app
        if self.ui.view.select_mode:
            self._select_mode_menu(app, e)
            return
        if app["id"] in self.ui.view.sel and len(self.ui.view.sel) > 1:
            self._selection_menu(e)
            return
        self.ui._select_tile(app["id"])

    def _select_mode_menu(self, app, e):
        x, y = self.menu_at(e)
        ids = list(self.ui.view.sel)
        picked = app["id"] in ids
        anchor = self.ui.view.selection_anchor
        rows = [
            menus.item(ft.Icons.CHECK_BOX if picked else ft.Icons.CHECK_BOX_OUTLINE_BLANK,
                       "Снять отметку" if picked else "Отметить",
                       lambda: self.ui._toggle_pick(app["id"])),
            menus.item(ft.Icons.SELECT_ALL, "Выбрать до этой",
                       lambda: self.ui._range_to(app["id"]),
                       disabled=not anchor or anchor == app["id"]),
            menus.item(ft.Icons.DONE_ALL, "Выбрать всё", self.ui._select_all_visible,
                       hint="" if self.ui.calm() else "Ctrl+A"),
        ]
        if ids:
            rows += [
                menus.separator(),
                menus.item(ft.Icons.FOLDER, "Переложить в…",
                           lambda: self.ui.menu.toggle_submenu(
                               "cat", self._category_submenu(ids), y), submenu=True),
                menus.item(ft.Icons.LAYERS, "В набор…",
                           lambda: self.ui.menu.toggle_submenu(
                               "set", self.set_submenu(ids), y), submenu=True),
                menus.item(ft.Icons.STAR_BORDER, "В избранное",
                           lambda: self.ui._bulk_favorite(ids)),
                menus.item(ft.Icons.VISIBILITY if self.ui.view.filter == "hidden"
                           else ft.Icons.VISIBILITY_OFF,
                           "Показать" if self.ui.view.filter == "hidden" else "Скрыть из сетки",
                           lambda: self.ui._hide_apps(ids, self.ui.view.filter != "hidden")),
                menus.item(ft.Icons.DELETE_OUTLINE, f"Убрать · {len(ids)}",
                           lambda: self.ui._remove_apps(ids), danger=True),
            ]
        rows += [menus.separator(),
                 menus.item(ft.Icons.CLOSE, "Выйти из режима", self.ui.toggle_select_mode,
                            hint="" if self.ui.calm() else "Esc")]
        header = (menus.text_header(f"Выбрано {len(ids)}") if ids
                  else menus.app_header(self.ui, app, app["id"] in self.ui.running))
        self.ui.menu.show(x, y, rows, header=header)

    def _selection_menu(self, e):
        x, y = self.menu_at(e)
        ids = list(self.ui.view.sel)
        count = len(ids)
        rows = [
            menus.item(ft.Icons.FOLDER, "Переложить в…",
                       lambda: self.ui.menu.toggle_submenu("cat", self._category_submenu(ids), y),
                       submenu=True),
            menus.item(ft.Icons.LAYERS, "В набор…",
                       lambda: self.ui.menu.toggle_submenu("set", self.set_submenu(ids), y),
                       submenu=True),
            menus.item(ft.Icons.STAR_BORDER, "В избранное", lambda: self.ui._bulk_favorite(ids)),
            menus.item(ft.Icons.VISIBILITY if self.ui.view.filter == "hidden"
                       else ft.Icons.VISIBILITY_OFF,
                       "Показать" if self.ui.view.filter == "hidden" else "Скрыть из сетки",
                       lambda: self.ui._hide_apps(ids, self.ui.view.filter != "hidden")),
            menus.separator(),
            menus.item(ft.Icons.DELETE_OUTLINE, f"Убрать · {count}",
                       lambda: self.ui._remove_apps(ids), danger=True),
        ]
        self.ui.menu.show(x, y, rows, header=menus.text_header(f"Выбрано {count}"))

    def category_menu(self, cat, e):
        x, y = self.menu_at(e)
        cats = self.ui.categories()
        index = [c["id"] for c in cats].index(cat["id"]) if cat["id"] in [c["id"] for c in cats] else 0
        count = sum(1 for a in self.ui.apps() if a.get("category_id") == cat["id"])
        rows = [
            menus.item(ft.Icons.EDIT, "Изменить", lambda: self.ui._open_popover(cat["id"])),
            menus.item(ft.Icons.ARROW_UPWARD, "Переместить выше",
                       lambda: self.ui._move_category(cat["id"], -1), disabled=index == 0),
            menus.item(ft.Icons.ARROW_DOWNWARD, "Переместить ниже",
                       lambda: self.ui._move_category(cat["id"], 1),
                       disabled=index >= len(cats) - 1),
            menus.separator(),
            menus.item(ft.Icons.DELETE_OUTLINE, "Удалить категорию",
                       lambda: self.ui._remove_category(cat["id"]), danger=True),
        ]
        self.ui.menu.show(x, y, rows, header=menus.category_header(self.ui, cat, count))

    def set_menu(self, rec, e):
        x, y = self.menu_at(e)
        accel = self.ui._set_accels.get(rec["id"])
        rows = [
            menus.item(ft.Icons.PLAY_ARROW, "Запустить набор",
                       lambda: self.ui.set_ops.launch_set(rec["id"]),
                       hint="" if self.ui.calm() else (accel or "")),
        ]
        if rec.get("close_together"):
            rows.append(menus.item(ft.Icons.CLOSE, "Закрыть набор",
                                   lambda: self.ui.set_ops.close_set_windows(rec["id"])))
        rows += [
            menus.item(ft.Icons.CROP_FREE, "Расставить окна",
                       lambda: self.ui.set_ops.arrange_set(rec["id"]),
                       disabled=not queries.has_layout(rec)),
            menus.item(ft.Icons.TUNE, "Раскладка и порядок",
                       lambda: self.ui._open_set(rec["id"])),
            menus.item(ft.Icons.BOLT,
                       "Убрать из быстрого запуска" if rec.get("quick") else "В быстрый запуск",
                       lambda: self.ui._toggle_set_quick(rec["id"], not rec.get("quick"))),
            menus.separator(),
            menus.item(ft.Icons.DELETE_OUTLINE, "Удалить набор",
                       lambda: self.ui.set_ops.remove_set(rec["id"]), danger=True),
        ]
        self.ui.menu.show(x, y, rows, header=menus.text_header(rec["name"]))

    def set_item_menu(self, rec, entry, e):
        x, y = self.menu_at(e)
        app = next((a for a in self.ui.apps() if a["id"] == entry["app_id"]), None)
        preset = rec["layout"]["preset"]
        places = [menus.item(ft.Icons.CHECK if entry.get("slot") == i else None,
                             L.slot_label(preset, i, rec["layout"]["split"]).capitalize(),
                             lambda idx=i: self.ui.set_ops.set_item_slot(rec["id"], entry["app_id"], idx))
                  for i in range(L.slot_count(preset))]
        places.append(menus.item(ft.Icons.CHECK if entry.get("slot") is None
                                 and not entry.get("minimized") else None,
                                 "Без места", lambda: self.ui.set_ops.set_item_slot(
                                     rec["id"], entry["app_id"], None)))
        rows = [
            menus.item(ft.Icons.ARROW_UPWARD, "Запускать раньше",
                       lambda: self.ui.set_ops.move_set_item(rec["id"], entry["app_id"], -1)),
            menus.item(ft.Icons.ARROW_DOWNWARD, "Запускать позже",
                       lambda: self.ui.set_ops.move_set_item(rec["id"], entry["app_id"], 1)),
            menus.separator(),
            menus.item(ft.Icons.CROP_FREE, "Место в раскладке",
                       lambda: self.ui.menu.toggle_submenu("slot", places, y), submenu=True),
            menus.item(ft.Icons.LAYERS_CLEAR if entry.get("minimized")
                       else ft.Icons.MINIMIZE,
                       "Открывать обычно" if entry.get("minimized") else "Запускать свёрнутым",
                       lambda: self.ui.set_ops.set_item_minimized(rec["id"], entry["app_id"],
                                                        not entry.get("minimized"))),
            menus.separator(),
            menus.item(ft.Icons.DELETE_OUTLINE, "Убрать из набора",
                       lambda: self.ui.set_ops.remove_from_set(rec["id"], entry["app_id"]),
                       danger=True),
        ]
        self.ui.menu.show(x, y, rows,
                       header=menus.text_header(app["name"] if app else "Программа"))

    def _category_submenu(self, app_ids):
        rows = []
        for cat in self.ui.categories():
            rows.append(menus.item(cat.get("icon") or "folder", cat["name"],
                                   lambda cid=cat["id"]: self.ui._move_apps_to_category(app_ids, cid)))
        return rows or [menus.item(None, "Категорий нет", None, disabled=True)]

    def set_submenu(self, app_ids):
        rows = [menus.item(ft.Icons.ADD, "Новый набор…", lambda: self.ui.set_ops.make_set(app_ids))]
        records = self.ui.sets()
        if records:
            rows.append(menus.separator())
        for rec in records:
            rows.append(menus.item(ft.Icons.LAYERS, rec["name"],
                                   lambda sid=rec["id"]: self.ui.set_ops.add_to_set(sid, app_ids)))
        return rows

    def _sort_submenu(self):
        return [menus.item(ft.Icons.CHECK if self.ui.view.sort == key else None,
                           queries.SORT_LABELS[key], lambda k=key: self.ui._set_sort(k))
                for key in queries.SORT_KEYS]

    def sort_menu(self, e):
        x, y = self.menu_at(e)
        self.ui.menu.show(x, y, self._sort_submenu(), header=None)

    def category_picker(self, app, e):
        x, y = self.menu_at(e)
        self.ui.menu.show(x, y, self._category_submenu([app["id"]]),
                       header=menus.text_header("Переложить в…"))

    def add_to_set_menu(self, app, e):
        x, y = self.menu_at(e)
        self.ui.menu.show(x, y, self.set_submenu([app["id"]]),
                       header=menus.text_header("Добавить в набор"))

    def launch_more_menu(self, app, e):
        x, y = self.menu_at(e)
        rows = [
            menus.item(ft.Icons.ADD, "Открыть ещё окно",
                       lambda: self.ui._launch(app["id"], again=True)),
            menus.item(ft.Icons.SHIELD, "От имени администратора",
                       lambda: self.ui._launch(app["id"], as_admin=True)),
        ]
        self.ui.menu.show(x, y, rows, header=None)

    def bulk_menu(self, kind: str):
        ids = list(self.ui.view.sel)
        if not ids:
            return
        rows = (self._category_submenu(ids) if kind == "cat" else self.set_submenu(ids))
        title = "Переложить в…" if kind == "cat" else "Добавить в набор…"
        self.ui.menu.show(self.ui._window_width() / 2 - 120, self.ui._window_height() - 96,
                       rows, header=menus.text_header(title))

    def monitor_menu(self, rec, e):
        x, y = self.menu_at(e)
        count = max(1, len(W.monitors()))
        rows = [menus.item(ft.Icons.CHECK if rec["monitor"] == i else None,
                           f"Монитор {i + 1}",
                           lambda idx=i: self.ui.set_ops.set_set_monitor(rec["id"], idx))
                for i in range(count)]
        self.ui.menu.show(x, y, rows, header=menus.text_header("Куда расставлять"))

    def delay_menu(self, rec, e):
        x, y = self.menu_at(e)
        rows = [menus.item(ft.Icons.CHECK if abs(rec["delay_seconds"] - value) < 0.01 else None,
                           "без паузы" if not value else f"{value:g} с",
                           lambda v=value: self.ui.set_ops.set_set_delay(rec["id"], v))
                for value in (0, 1, 2, 4, 8)]
        self.ui.menu.show(x, y, rows, header=menus.text_header("Пауза между запусками"))

    def add_to_set_picker(self, set_id, e=None):
        rec = self.ui.store.get_set(set_id)
        if not rec:
            return
        inside = set(rec["apps"])
        rows = [menus.item(None, a["name"], lambda aid=a["id"]: self.ui.set_ops.add_to_set(set_id, [aid]))
                for a in sorted(queries.visible(self.ui.apps()), key=lambda a: a["name"].lower())
                if a["id"] not in inside]
        if not rows:
            self.ui.notify.show("В наборе уже всё, что есть в библиотеке", icon="layers",
                                tone="muted")
            return
        x, y = self.menu_at(e)
        self.ui.menu.show(x, y, rows[:14], header=menus.text_header("Добавить в набор"))
