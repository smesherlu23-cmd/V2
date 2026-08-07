from __future__ import annotations

import flet as ft

from .. import __version__
from ..core import queries
from ..core.text import plu_hits
from ..infra import log
from . import colors as C
from . import widgets as Wg
from .format import T

HEADER_SIDES_W = 320


class Chrome:
    def __init__(self, ui):
        self.ui = ui

    def sync_search_box(self, matches: int = 0):
        from ..core.hotkeys import format_accel
        active = self.ui.view.palette_open
        room = self.ui._window_width() - HEADER_SIDES_W
        self.ui.search_box.width = max(C.SEARCH_MIN_W, min(C.SEARCH_W, room))
        self.ui.search_box.bgcolor = C.FIELD_ACTIVE_BG if active else C.PANEL
        self.ui.search_box.border = ft.border.all(
            1, C.FIELD_ACTIVE_BORDER if active else C.CONTROL)
        self.ui.search_icon.color = C.TEXT_2 if active else C.MUTED_2
        if active:
            tail = []
            if self.ui.view.query.strip() and not self.ui.calm():
                tail.append(T(f"{matches} {plu_hits(matches)}", size=11, color=C.MUTED_2))
            tail.append(ft.Container(ft.Icon(ft.Icons.CLOSE, size=15, color=C.MUTED_2),
                                     tooltip="Закрыть поиск",
                                     on_click=lambda e: self.ui._close_palette()))
            self.ui.search_tail.content = ft.Row(tail, spacing=10, tight=True,
                                              vertical_alignment=ft.CrossAxisAlignment.CENTER)
        elif self.ui.calm():
            self.ui.search_tail.content = None
        else:
            self.ui.search_tail.content = Wg.key_chip(
                format_accel(self.ui.setting("launch_hotkey")), self.ui._accent())

    def build_header(self):
        logo = ft.WindowDragArea(
            ft.Container(T("Centurio", size=13.5, weight=ft.FontWeight.BOLD, color=C.TEXT),
                         width=150, padding=ft.padding.only(18, 0, 0, 0),
                         alignment=ft.alignment.center_left))
        centre = ft.Container(
            ft.Row([ft.WindowDragArea(ft.Container(height=36), expand=True),
                    self.ui.search_box,
                    ft.WindowDragArea(ft.Container(height=36), expand=True)],
                   spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            expand=True)
        buttons = ft.Container(
            ft.Row([Wg.win_btn(ft.Icons.REMOVE, "Свернуть", self.ui._minimize),
                    Wg.win_btn(ft.Icons.CROP_SQUARE, "Развернуть", self.ui._toggle_maximize),
                    Wg.win_btn(ft.Icons.CLOSE, "Закрыть", self.ui._close, danger=True)],
                   spacing=2, alignment=ft.MainAxisAlignment.END),
            width=150, alignment=ft.alignment.center_right)
        return ft.Container(
            ft.Row([logo, centre, buttons], spacing=16,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            height=C.HEADER_H, bgcolor=C.BG_1,
            border=ft.border.only(bottom=ft.BorderSide(1, C.LINE_2)),
            padding=ft.padding.only(0, 0, 6, 0),
        )

    def _rail_item(self, glyph, active, on_click, tooltip, fixed_color=None,
                   on_drop_app=None, on_drop_category=None, on_context=None,
                   badge=None, outlined=False):
        btn = self.ui.rail()["btn"]
        # Discord's squircle-on-select: a circle at rest, rounded square when
        # active. Both radii track the button so the shape reads the same at
        # every rail scale.
        round_r, square_r = btn / 2, btn / 3
        inner = ft.Container(
            glyph, width=btn, height=btn,
            border_radius=square_r if active else round_r,
            bgcolor=C.PANEL_ACTIVE if active else C.RAIL_BTN_BG,
            border=ft.border.all(1, C.LINE_4) if outlined else None,
            alignment=ft.alignment.center, tooltip=tooltip,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            animate=ft.Animation(C.ANIM_BAR, ft.AnimationCurve.EASE_OUT),
        )

        def on_hover(e):
            if active:
                return
            highlight = e.data == "true"
            inner.bgcolor = C.PANEL_ACTIVE if highlight else C.RAIL_BTN_BG
            inner.border_radius = square_r if highlight else round_r
            if fixed_color is None and isinstance(inner.content, ft.Icon):
                inner.content.color = C.TEXT if highlight else C.MUTED
            Wg.safe_update(inner)
        inner.on_hover = on_hover

        button = inner
        if badge is not None:
            button = ft.Stack([inner, ft.Container(badge, right=-3, top=-3)],
                              width=btn + 6, height=btn + 6)

        tapper = ft.GestureDetector(
            button, mouse_cursor=ft.MouseCursor.CLICK,
            on_tap=lambda e: on_click(),
            on_secondary_tap_down=(lambda e: on_context(e)) if on_context else None)

        content = tapper
        if on_drop_app is not None or on_drop_category is not None:
            def _accept(e):
                src = self.ui.page.get_control(e.src_id)
                payload = getattr(src, "data", None) if src is not None else None
                inner.border = ft.border.all(1, C.LINE_4) if outlined else None
                Wg.safe_update(inner)
                # A dragged category tile and a dragged app tile share the
                # "apps" DragTarget group (Flet targets can only listen to
                # one group at a time) — the dict shape tells them apart.
                if isinstance(payload, dict) and payload.get("category_id"):
                    if on_drop_category:
                        on_drop_category(payload["category_id"])
                elif on_drop_app is not None:
                    if isinstance(payload, dict) and payload.get("ids"):
                        on_drop_app(payload["ids"])
                    elif payload:
                        on_drop_app([payload])

            def _will(e):
                inner.border = ft.border.all(2, self.ui._accent())
                Wg.safe_update(inner)

            def _leave(e):
                inner.border = ft.border.all(1, C.LINE_4) if outlined else None
                Wg.safe_update(inner)
            content = ft.DragTarget(group="apps", content=tapper,
                                    on_accept=_accept, on_will_accept=_will, on_leave=_leave)

        bar = ft.Container(width=3, height=round(btn * 0.62),
                           border_radius=ft.border_radius.only(0, 3, 0, 3),
                           bgcolor=self.ui._accent()) if active else ft.Container(width=3)
        return ft.Row([bar, ft.Container(content, expand=True, alignment=ft.alignment.center)],
                      spacing=0)

    def _inbox_badge(self, count: int):
        return ft.Container(
            T(str(count if count < 100 else 99), size=10, weight=ft.FontWeight.BOLD,
              color=C.ON_ACCENT, font_family="monospace"),
            height=17, border_radius=9, bgcolor=self.ui._accent(),
            padding=ft.padding.symmetric(0, 5), alignment=ft.alignment.center)

    def _on_rail_scroll(self, e: ft.OnScrollEvent):
        self.ui._rail_scroll = e.pixels or 0.0

    def build_rail(self):
        """The category rail: fixed top and bottom, a scrolling middle.

        At the "huge" scale, or with enough categories, the full list no
        longer fits between the window's top and bottom — with the old
        single non-scrolling Column that meant the add-category button and
        everything below it (Разбор, Настройки) became simply unreachable.
        Only the categories scroll now; the two always-there buttons above
        the divider and the two below stay put, the way a real sidebar does.
        """
        self.ui._rail_scroll = 0.0
        on_grid = self.ui.view.screen == "grid" and not self.ui.view.active_set
        all_active = self.ui.is_all_view() and on_grid
        waiting = len(self.ui.inbox())
        metrics = self.ui.rail()
        btn, glyph, gap = metrics["btn"], metrics["glyph"], metrics["gap"]

        top = [
            self._rail_item(ft.Icon(ft.Icons.GRID_VIEW, size=glyph,
                                    color=C.TEXT if all_active else C.MUTED),
                            all_active, lambda: self.ui._set_filter("all"), "Все программы"),
            self._rail_item(ft.Icon(ft.Icons.VIEW_SIDEBAR, size=glyph - 1,
                                    color=C.TEXT if self.ui.view.sidebar_open else C.MUTED),
                            self.ui.view.sidebar_open, lambda: self.ui._toggle_sidebar(),
                            "Показать/скрыть панель"),
            ft.Container(width=round(btn * 0.72), height=1, bgcolor=C.LINE_2,
                         margin=ft.margin.symmetric(3, 0)),
        ]

        cats = []
        for cat in self.ui.categories():
            active = self.ui.view.filter == f"category:{cat['id']}" and on_grid
            item = self._rail_item(
                Wg.cat_glyph(cat, size=glyph, color=C.TEXT if active else None,
                             fill=btn), active,
                lambda cid=cat["id"]: self.ui._set_filter(f"category:{cid}"), cat["name"],
                fixed_color=C.category_color(cat),
                on_drop_app=lambda ids, cid=cat["id"]: self.ui._move_apps_to_category(ids, cid),
                on_drop_category=lambda dragged, cid=cat["id"]: self.ui._reorder_category(
                    dragged, cid),
                on_context=lambda e, c=cat: self.ui.context_menus.category_menu(c, e))
            # Draggable so the tile can be dragged onto another category to
            # reorder — a raw drag of the badge itself, not just the
            # existing up/down menu entries. Same "apps" group as app tiles
            # (see _rail_item._accept): the {"category_id": ...} shape is
            # what tells the two kinds of drop apart.
            cats.append(ft.Draggable(group="apps", content=item,
                                     data={"category_id": cat["id"]}))
        add = ft.Container(ft.Icon(ft.Icons.ADD, size=glyph - 3, color=C.TEXT_FAINT),
                           width=btn, height=btn, border_radius=btn / 2,
                           alignment=ft.alignment.center,
                           border=ft.border.all(1.5, C.CONTROL),
                           on_click=lambda e: self.ui._add_category(),
                           tooltip="Добавить категорию")
        cats.append(ft.Row([ft.Container(width=3),
                            ft.Container(add, expand=True, alignment=ft.alignment.center)],
                           spacing=0))
        middle = ft.Container(
            ft.Column(cats, spacing=gap, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                      scroll=ft.ScrollMode.AUTO, on_scroll=self._on_rail_scroll, expand=True),
            expand=True)

        triage_active = self.ui.view.screen == "triage"
        bottom = [
            self._rail_item(
                ft.Icon(ft.Icons.INBOX, size=glyph - 1,
                       color=C.TEXT if triage_active else C.TEXT_2),
                triage_active, lambda: self.ui.open_triage(),
                f"Разбор · {waiting}" if waiting and not self.ui.calm() else "Разбор",
                badge=self._inbox_badge(waiting) if waiting and not self.ui.calm() else None,
                outlined=True),
            ft.Container(height=4),
            ft.Container(ft.Icon(ft.Icons.SETTINGS, size=glyph - 1,
                                 color=C.TEXT if self.ui.view.screen == "settings"
                                 else C.MUTED_2),
                        width=btn, height=btn, border_radius=btn / 2,
                        alignment=ft.alignment.center,
                        on_click=lambda e: self.ui._open_settings(), tooltip="Настройки"),
        ]

        return ft.Container(
            ft.Column(top + [middle] + bottom, spacing=gap,
                      horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True),
            padding=ft.padding.only(0, 14, 0, 12),
            border=ft.border.only(right=ft.BorderSide(1, C.LINE_2)), expand=True,
        )

    def _sidebar_filter(self, icon_ctl, label, count, key, count_color=None):
        active = self.ui.view.filter == key and self.ui.view.screen == "grid" and not self.ui.view.active_set
        row = ft.Container(
            ft.Row([
                ft.Container(icon_ctl, width=16, height=16, alignment=ft.alignment.center),
                T(label, size=13, color=C.TEXT if active else C.TEXT_2,
                  weight=ft.FontWeight.W_600 if active else ft.FontWeight.W_400, expand=True),
                T("" if self.ui.calm() else str(count), size=11,
                  color=count_color or C.MUTED_2, font_family="monospace"),
            ], spacing=11),
            padding=ft.padding.symmetric(7, 10), border_radius=9,
            bgcolor=C.SET_SLOT_BG if active else None,
            border=ft.border.all(1, C.CONTROL) if active else None,
            on_click=lambda e: self.ui._set_filter(key),
        )
        if not active:
            Wg.hoverable(row, None, C.SET_SLOT_BG)
        return row

    def build_sidebar(self):
        apps = self.ui.apps()
        shown = queries.visible(apps)
        fav = sum(1 for a in shown if a.get("favorite"))
        recent_count = sum(1 for a in shown if a.get("last_launched"))
        buried = sum(1 for a in apps if a.get("hidden"))

        top = [ft.Container(T(self.ui._current_title(), size=18, weight=ft.FontWeight.BOLD,
                              color=C.TEXT, max_lines=1,
                              overflow=ft.TextOverflow.ELLIPSIS),
                            padding=ft.padding.only(8, 0, 8, 0))]
        if not self.ui.calm():
            total = len(self.ui.visible_apps())
            subtitle = (f"{total} · выбрано {len(self.ui.view.sel)}"
                        if self.ui.view.select_mode else str(total))
            top.append(ft.Container(T(subtitle, size=11.5, color=C.MUTED_2, no_wrap=True,
                                      overflow=ft.TextOverflow.ELLIPSIS),
                                    padding=ft.padding.only(8, 4, 8, 0)))
        top += [
            ft.Container(height=1, bgcolor=C.LINE_2, margin=ft.margin.symmetric(10, 0)),
            self._sidebar_filter(ft.Icon(ft.Icons.STAR, size=16, color=C.STAR),
                                 "Избранное", fav, "favorites"),
            self._sidebar_filter(ft.Icon(ft.Icons.SCHEDULE, size=16, color=C.MUTED),
                                 "Недавние", recent_count, "recent"),
            self._sidebar_filter(Wg.dot(8), "Запущено", len(self.ui.running), "running",
                                 C.GREEN),
        ]
        if buried:
            top.append(self._sidebar_filter(
                ft.Icon(ft.Icons.VISIBILITY_OFF, size=16, color=C.MUTED),
                "Скрытые", buried, "hidden"))

        top += [ft.Container(height=1, bgcolor=C.LINE_2, margin=ft.margin.symmetric(10, 0)),
                ft.Container(ft.Row([Wg.caps("НАБОРЫ"), ft.Container(expand=True),
                                     ft.Container(ft.Icon(ft.Icons.ADD, size=15,
                                                          color=C.MUTED_2),
                                                  tooltip="Собрать набор из выбранного",
                                                  on_click=lambda e: self.ui.set_ops.new_set())],
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER),
                             padding=ft.padding.only(10, 0, 10, 8))]

        sets_block = []
        if self.ui.view.select_mode:
            sets_block.append(self._set_drop_hint())
        records = self.ui.sets()
        for rec in records:
            sets_block.append(self._sidebar_set_row(rec))
        if not records and not self.ui.view.select_mode:
            sets_block.append(ft.Container(
                T("Выберите плитки и нажмите «плюс»", size=11.5, color=C.TEXT_DIM),
                padding=ft.padding.only(10, 0, 10, 4)))
        return ft.Container(
            ft.Column([ft.Column(top, spacing=3, tight=True),
                       ft.Column(sets_block, spacing=3, expand=True,
                                 scroll=ft.ScrollMode.AUTO),
                       self._sidebar_footer()],
                      spacing=3, expand=True),
            padding=ft.padding.only(14, 20, 14, 12),
            border=ft.border.only(right=ft.BorderSide(1, C.LINE_2)), expand=True,
        )

    def _sidebar_set_row(self, rec):
        active = self.ui.view.active_set == rec["id"]
        lines = [T(rec["name"], size=12.5, weight=ft.FontWeight.W_500,
                   color=C.TEXT if active else C.TEXT_2, max_lines=1,
                   overflow=ft.TextOverflow.ELLIPSIS)]
        if not (self.ui.calm() or self.ui.view.select_mode):
            lines.append(T(queries.set_summary(rec), size=10.5, color=C.MUTED_2,
                           max_lines=1, overflow=ft.TextOverflow.ELLIPSIS))
        row = ft.Container(
            ft.Row([ft.Container(ft.Icon(ft.Icons.LAYERS, size=16,
                                         color=C.TEXT_2 if active else C.MUTED),
                                 width=16, height=16, alignment=ft.alignment.center),
                    ft.Column(lines, spacing=1, expand=True, tight=True)], spacing=10),
            padding=ft.padding.symmetric(8, 10), border_radius=9,
            bgcolor=C.SET_SLOT_BG if active else None,
            border=ft.border.all(1, C.CONTROL) if active else None,
            on_click=lambda e, sid=rec["id"]: self.ui._open_set(sid))
        if not active:
            Wg.hoverable(row, None, C.SET_SLOT_BG)
        rest = C.CONTROL if active else None
        return ft.DragTarget(
            group="apps", content=ft.GestureDetector(
                row, on_secondary_tap_down=lambda e, r=rec: self.ui.context_menus.set_menu(r, e)),
            on_accept=lambda e, sid=rec["id"]: self._drop_on_set(sid, e, row, rest),
            on_will_accept=lambda e, r=row: self.highlight_drop(r, True, rest),
            on_leave=lambda e, r=row: self.highlight_drop(r, False, rest))

    def _set_drop_hint(self):
        row = ft.Container(
            ft.Row([ft.Container(ft.Icon(ft.Icons.LAYERS, size=16, color=C.MUTED),
                                 width=16, height=16, alignment=ft.alignment.center),
                    T("Перетащите сюда", size=12, color=C.MUTED, expand=True,
                      max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)],
                   spacing=10),
            padding=ft.padding.symmetric(8, 10), border_radius=9,
            border=ft.border.all(1, C.BAR_BORDER),
            on_click=lambda e: self.ui.set_ops.new_set())
        return ft.DragTarget(
            group="apps", content=row,
            on_accept=lambda e, r=row: self._drop_new_set(e, r),
            on_will_accept=lambda e, r=row: self.highlight_drop(r, True, C.BAR_BORDER),
            on_leave=lambda e, r=row: self.highlight_drop(r, False, C.BAR_BORDER))

    def highlight_drop(self, row, on: bool, rest=None):
        row.border = (ft.border.all(1, self.ui._accent()) if on
                      else (ft.border.all(1, rest) if rest else None))
        try:
            row.update()
        except Exception:
            log.exception("сбой при обновлении интерфейса после перетаскивания")

    def drop_set_item(self, set_id, target_id, e, row, rest=C.LINE):
        self.highlight_drop(row, False, rest)
        src = self.ui.page.get_control(e.src_id)
        moved = getattr(src, "data", None) if src is not None else None
        rec = self.ui.store.get_set(set_id)
        if not rec or not isinstance(moved, str) or moved == target_id:
            return
        order = [i["app_id"] for i in rec["items"] if i["app_id"] != moved]
        if target_id not in order:
            return
        order.insert(order.index(target_id), moved)
        self.ui.store.reorder_set_items(set_id, order)
        self.ui.refresh()

    def _dropped_ids(self, e) -> list[str]:
        src = self.ui.page.get_control(e.src_id)
        payload = getattr(src, "data", None) if src is not None else None
        if isinstance(payload, dict) and payload.get("ids"):
            return list(payload["ids"])
        return [payload] if payload else []

    def _drop_on_set(self, set_id, e, row, rest=None):
        self.highlight_drop(row, False, rest)
        ids = self._dropped_ids(e)
        if ids:
            self.ui.set_ops.add_to_set(set_id, ids)

    def _drop_new_set(self, e, row):
        self.highlight_drop(row, False, C.BAR_BORDER)
        ids = self._dropped_ids(e)
        if ids:
            self.ui.set_ops.make_set(ids)

    def _sidebar_footer(self):
        left = T("" if self.ui.calm() or not self.ui.running
                 else f"{len(self.ui.running)} запущено", size=11, color=C.MUTED_3)
        return ft.Container(
            ft.Row([left,
                    T(f"v{__version__}", size=11, color=C.MUTED_3, font_family="monospace")],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            border=ft.border.only(top=ft.BorderSide(1, C.LINE_2)),
            padding=ft.padding.only(10, 10, 10, 0),
        )

    def build_toolbar(self):
        select = Wg.outline_btn(
            "Выбрать",
            self.ui.toggle_select_mode,
            ft.Icons.CHECK_BOX if self.ui.view.select_mode
            else ft.Icons.CHECK_BOX_OUTLINE_BLANK,
            active=self.ui.view.select_mode)
        left = [select]
        if self.ui.view.select_mode:
            label = ("Выбрать всё" if self.ui.is_all_view()
                     else f"Выбрать всё в «{self.ui._current_title()}»")
            left.append(Wg.outline_btn(label, self.ui._select_all_visible))
        sort_btn = ft.Container(
            ft.Row([T(queries.SORT_LABELS[self.ui.view.sort], size=12.5, color=C.MUTED),
                    ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN, size=14, color=C.MUTED_2)],
                   spacing=7),
            height=34, padding=ft.padding.symmetric(0, 12),
            border=ft.border.all(1, C.CONTROL), border_radius=9,
            on_click=lambda e: self.ui.context_menus.sort_menu(e), alignment=ft.alignment.center,
            tooltip="Порядок плиток",
        )
        Wg.hoverable(sort_btn, None, C.SELECTED_BG)

        def view_btn(icon_name, m, tip):
            active = self.ui.view.mode == m
            return ft.Container(ft.Icon(icon_name, size=13,
                                        color=C.TEXT if active else C.MUTED_2),
                                width=34, height=34, alignment=ft.alignment.center,
                                bgcolor=C.PANEL_ACTIVE if active else None,
                                on_click=lambda e: self.ui._set_mode(m), tooltip=tip)
        view_toggle = ft.Container(
            ft.Row([view_btn(ft.Icons.GRID_VIEW, "grid", "Сетка"),
                    view_btn(ft.Icons.VIEW_LIST, "list", "Список")], spacing=0),
            border=ft.border.all(1, C.CONTROL), border_radius=9,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )
        right = (T("Клик — отметить · Ctrl+A — всё · правая кнопка — до этой",
                   size=11.5, color=C.MUTED_2)
                 if self.ui.view.select_mode and not self.ui.calm() else
                 Wg.primary_btn("Добавить", self.ui.open_add, self.ui._accent(), self.ui.calm(),
                               ft.Icons.ADD, height=34))
        return ft.Container(
            ft.Row(left + [sort_btn, view_toggle, ft.Container(expand=True), right],
                   spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.only(22, 16, 22, 10),
        )
