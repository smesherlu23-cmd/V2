from __future__ import annotations

import flet as ft

from ..core import queries
from ..core.hotkeys import free_quick_slot
from ..core.text import short_ago
from . import colors as C
from . import screens
from . import widgets as Wg
from .format import T
from .images import img_b64, is_launcher_art

QUICK_H = 88


class GridView:
    def __init__(self, ui):
        self.ui = ui

    def build_content(self):
        screen = self.ui.view.screen
        if screen == "add":
            return [screens.build_add_screen(self.ui)]
        if screen == "settings":
            return [screens.build_settings_screen(self.ui)]
        if screen == "triage":
            return [screens.build_triage_screen(self.ui)]
        if self.ui.view.active_set:
            rec = next((s for s in self.ui.sets() if s["id"] == self.ui.view.active_set), None)
            if rec is not None:
                return [screens.build_set_screen(self.ui, rec)]

        apps = self.ui.apps()
        if not apps and not self.ui.sets():
            self.ui._sel_id = None
            return [self._empty("Библиотека пуста",
                                "Centurio посмотрит, что установлено, и предложит отметить "
                                "нужное. Можно и указать файл вручную.",
                                "Найти и добавить", self.ui.open_add)]

        sections = self.ui.sections()
        self.ui._sel_id = self.ui._selected_id(sections)

        controls = []
        if self.ui.is_all_view() and self.ui.setting("show_quick_row", True) \
                and not self.ui.view.select_mode:
            controls += self._quick_row()

        if not sections or all(not s["apps"] for s in sections):
            controls.append(self._empty_section())
            return controls

        for sec in sections:
            if not sec["apps"]:
                continue
            controls.append(self._section_head(sec))
            if sec.get("cid") and sec["cid"] in self.ui.view.collapsed \
                    and not self.ui.view.select_mode:
                continue
            controls.append(self._grid(sec["apps"]) if self.ui.view.mode == "grid"
                            else self._list(sec["apps"]))
        controls.append(ft.Container(height=self._bottom_gap()))
        return controls

    def _bottom_gap(self) -> int:
        return 96 if self.ui.view.select_mode and self.ui.view.sel else 12

    def _empty_section(self):
        if self.ui.view.filter == "hidden":
            return self._empty("Ничего не скрыто",
                               "«Скрыть» в панели массовых операций убирает плитки "
                               "отсюда, не удаляя их.", None, None)
        return self._empty("Здесь пока пусто",
                           "Добавьте программы — или перетащите плитку на значок "
                           "категории слева.", "Добавить", self.ui.open_add)

    def _quick_row(self):
        cards = [self._set_card(s) for s in self.ui.sets() if s.get("quick")]
        for app in queries.quick_apps(queries.visible(self.ui.apps())):
            cards.append(self._quick_card(app, self.ui._accels.get(app["id"])))
        free = free_quick_slot(self.ui.apps())
        if free and self._fits_in_row(len(cards)):
            cards.append(self._quick_empty(free))

        head_row = [T("Быстрый запуск", size=14.5, weight=ft.FontWeight.BOLD, color=C.TEXT)]
        if not self.ui.calm():
            head_row.append(T("Ctrl+1…9", size=11, color=C.MUTED_2, font_family="monospace"))
        head = ft.Container(ft.Row(head_row, spacing=10), padding=ft.padding.only(0, 8, 0, 12))
        return [head, ft.Container(ft.Row(cards, spacing=10, wrap=True, run_spacing=10),
                                   padding=ft.padding.only(0, 0, 0, 18))]

    def _fits_in_row(self, count: int) -> bool:
        gap = 10
        per_row = max(1, int((self.ui._content_width() - 44 + gap) // (C.QUICK_W + gap)))
        return count % per_row != 0

    def _quick_card(self, app, accel):
        layers = [ft.Column([
            self.ui.icon_slot(app, 38, 11, glyph=20),
            ft.Container(height=8),
            T(app["name"], size=12.5, weight=ft.FontWeight.W_600, color=C.TEXT,
              max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
        ], spacing=0, tight=True)]
        if accel and not self.ui.calm():
            layers.append(ft.Container(
                T(accel.split("+")[-1], size=10.5, weight=ft.FontWeight.W_600,
                  color=C.TEXT_FAINT, font_family="monospace"), right=9, top=9))
        card = ft.Container(
            ft.Stack(layers), width=C.QUICK_W, height=QUICK_H, bgcolor=C.PANEL,
            border=ft.border.all(1, C.CONTROL), border_radius=12,
            padding=ft.padding.all(12),
            on_click=lambda e, i=app["id"]: self.ui._launch(i))
        Wg.hoverable(card, C.PANEL, C.SELECTED_BG)
        return ft.GestureDetector(card,
                                  on_secondary_tap_down=lambda e, ap=app: self.ui.context_menus.app_menu(ap, e))

    def _set_card(self, rec):
        accel = self.ui._set_accels.get(rec["id"])
        card = ft.Container(
            ft.Column([
                Wg.set_slot(38, 11, 19, muted=True),
                ft.Container(height=8),
                T(rec["name"], size=12.5, weight=ft.FontWeight.W_600, color=C.TEXT_2,
                  max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            ], spacing=0, tight=True),
            width=C.QUICK_W, height=QUICK_H, bgcolor=C.SET_BG,
            border=ft.border.all(1, C.DASHED), border_radius=12,
            padding=ft.padding.all(12),
            tooltip=f"{rec['name']} · {accel}" if accel and not self.ui.calm() else rec["name"],
            on_click=lambda e, sid=rec["id"]: self.ui.set_ops.launch_set(sid))
        Wg.hoverable(card, C.SET_BG, C.PANEL)
        return ft.GestureDetector(card,
                                  on_secondary_tap_down=lambda e, r=rec: self.ui.context_menus.set_menu(r, e))

    def _quick_empty(self, slot):
        return ft.Container(
            ft.Icon(ft.Icons.ADD, size=16, color=C.TEXT_GHOST),
            width=C.QUICK_W, height=QUICK_H, border_radius=12,
            border=ft.border.all(1, C.CONTROL), alignment=ft.alignment.center,
            tooltip=f"Закрепите приложение — оно встанет на Ctrl+{slot}",
            on_click=lambda e: self.ui._toast_hint_quick())

    def _section_head(self, sec):
        cat = next((c for c in self.ui.categories() if c["id"] == sec.get("cid")), None)
        collapsed = bool(sec.get("cid")) and sec["cid"] in self.ui.view.collapsed
        row = [Wg.cat_glyph(cat, size=14) if cat
               else ft.Container(width=8, height=8, border_radius=4, bgcolor=C.DOT),
               T(sec["name"], size=14.5, weight=ft.FontWeight.BOLD, color=C.TEXT)]
        if not self.ui.calm():
            total = len(sec["apps"])
            picked = sum(1 for a in sec["apps"] if a["id"] in self.ui.view.sel)
            label = f"{total} · выбрано {picked}" if self.ui.view.select_mode else str(total)
            row.append(T(label, size=11, color=C.MUTED_2))
        row.append(ft.Container(height=1, bgcolor=C.LINE_2, expand=True))
        if sec.get("cid") and not self.ui.view.select_mode:
            row.append(ft.Container(
                ft.Icon(ft.Icons.EXPAND_MORE if collapsed else ft.Icons.EXPAND_LESS,
                        size=16, color=C.TEXT_FAINT),
                tooltip="Развернуть" if collapsed else "Свернуть",
                on_click=lambda e, cid=sec["cid"]: self.ui._toggle_section(cid)))
        head = ft.Container(ft.Row(row, spacing=9,
                                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
                            padding=ft.padding.only(0, 2, 0, 12))
        if not cat:
            return head
        return ft.GestureDetector(head,
                                  on_secondary_tap_down=lambda e, c=cat: self.ui.context_menus.category_menu(c, e))

    def _use_poster(self, a):
        return bool(self.ui._settings.get("game_posters", True)
                    and is_launcher_art(a) and img_b64(a.get("poster")))

    def _grid(self, apps):
        ids = [a["id"] for a in apps]
        ids_key = hash(tuple(ids))
        tiles = [self._draggable_tile(a, ids, ids_key) for a in apps]
        return ft.Container(ft.Row(tiles, wrap=True, spacing=12, run_spacing=12,
                                   vertical_alignment=ft.CrossAxisAlignment.START),
                            padding=ft.padding.only(0, 0, 0, 18))

    def _tile_signature(self, a, ids_key, running, selected, picked, cat):
        return (self.ui._tile_epoch, ids_key, running, selected, picked,
                self.ui._accels.get(a["id"]),
                tuple(self.ui.view.sel) if picked else None,
                self.ui.window_count(a) if running else 0,
                a.get("name"), a.get("path"), a.get("sub"), a.get("source"),
                a.get("icon"), a.get("icon_fit"), a.get("poster"),
                a.get("category_id"), bool(a.get("favorite")),
                bool(a.get("hidden")), bool(a.get("quick")),
                a.get("last_launched"),
                (cat.get("name"), cat.get("icon"), cat.get("color"), cat.get("image"))
                if cat else None)

    def _draggable_tile(self, a, ids, ids_key):
        app_id = a["id"]
        running = app_id in self.ui.running
        picked = app_id in self.ui.view.sel
        selected = picked or (not self.ui.view.select_mode and app_id == self.ui._sel_id)
        cat = self.ui.cat_of(a)
        sig = self._tile_signature(a, ids_key, running, selected, picked, cat)
        self.ui._tiles_used.add(app_id)
        hit = self.ui._tile_cache.get(app_id)
        if hit is not None and hit[0] == sig:
            self.ui._tile_cache.move_to_end(app_id)
            return hit[1]
        compact = self.ui._settings.get("tile_size") == "compact"
        base = (self._build_poster_tile(a, compact, running, selected, ids)
                if self._use_poster(a) else
                self._build_tile(a, compact, running, selected, ids))
        tile = ft.Draggable(group="apps", content=base,
                            data={"ids": self.ui._drag_ids(app_id)})
        self.ui._tile_cache[app_id] = (sig, tile)
        self.ui._tile_cache.move_to_end(app_id)
        return tile

    def _tile_meta(self, app, cat) -> str:
        if self.ui.calm():
            return ""
        if self.ui.view.select_mode:
            return cat["name"] if cat else ""
        accel = self.ui._accels.get(app["id"])
        if accel:
            return accel
        ago = short_ago(app.get("last_launched"))
        if ago:
            return ago
        if cat:
            return cat["name"]
        return (app.get("sub") or "").strip()

    def _tile_marks(self, a, running):
        if self.ui.view.select_mode:
            picked = a["id"] in self.ui.view.sel
            box = ft.Container(
                ft.Icon(ft.Icons.CHECK, size=14, color=C.ON_ACCENT) if picked else None,
                width=20, height=20, border_radius=10,
                bgcolor=self.ui._accent() if picked else None,
                border=None if picked else ft.border.all(1.5, C.TEXT_FAINT),
                alignment=ft.alignment.center)
            return [ft.Container(box, left=8, top=8)]
        marks = []
        if running:
            marks.append(ft.Container(Wg.dot(), left=9, top=9,
                                      tooltip=self.ui.running_note(a)))
        if a.get("favorite"):
            marks.append(ft.Container(ft.Icon(ft.Icons.STAR, size=14, color=C.STAR),
                                      right=9, top=9, tooltip="В избранном"))
        return marks

    def _build_tile(self, a, compact, running, selected, ids):
        width = C.TILE_W_COMPACT if compact else C.TILE_W
        cover_h = C.TILE_COVER_H_COMPACT if compact else C.TILE_COVER_H
        slot = C.TILE_SLOT_COMPACT if compact else C.TILE_SLOT
        cat = self.ui.cat_of(a)

        gradient = C.TILE_GRADIENT_SEL if selected else C.TILE_GRADIENT
        cover_children = [ft.Container(
            self.ui.icon_slot(a, slot, 14, glyph=round(slot * 0.48),
                           border=C.SLOT_BORDER_SEL if selected else None,
                           glyph_color=C.SLOT_GLYPH_SEL if selected else None),
            expand=True, alignment=ft.alignment.center,
            gradient=ft.LinearGradient(begin=ft.alignment.top_left,
                                       end=ft.alignment.bottom_right,
                                       colors=list(gradient)))]
        cover_children += self._tile_marks(a, running)

        meta = self._tile_meta(a, cat)
        foot_lines = [T(a["name"], size=12.5, weight=ft.FontWeight.W_600, color=C.TEXT,
                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)]
        if meta:
            foot_lines.append(T(meta, size=10.5, color=C.MUTED_2, max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                                font_family="monospace" if meta.startswith("Ctrl") else None))
        foot = ft.Container(ft.Column(foot_lines, spacing=2, tight=True),
                            padding=ft.padding.only(11, 9, 11, 10))

        tile = ft.Container(
            ft.Column([ft.Container(ft.Stack(cover_children, expand=True),
                                    height=cover_h - (2 if selected else 0),
                                    clip_behavior=ft.ClipBehavior.HARD_EDGE), foot],
                      spacing=0, tight=True),
            width=width, bgcolor=C.SELECTED_BG if selected else C.PANEL,
            border=ft.border.all(2, self.ui._accent()) if selected else ft.border.all(1, C.LINE),
            border_radius=14, clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )

        def on_hover(e):
            if selected:
                return
            hot = e.data == "true"
            tile.border = ft.border.all(1, C.LINE_4 if hot else C.LINE)
            tile.bgcolor = C.SELECTED_BG if hot else C.PANEL
            Wg.safe_update(tile)
        tile.on_hover = on_hover
        return self._tile_gestures(tile, a, ids)

    def _build_poster_tile(self, a, compact, running, selected, ids):
        width = C.POSTER_W_COMPACT if compact else C.POSTER_W
        height = C.POSTER_H_COMPACT if compact else C.POSTER_H
        poster = ft.Image(src_base64=img_b64(a.get("poster")), width=width, height=height,
                          fit=ft.ImageFit.COVER)
        scrim = ft.Container(
            T(a["name"], size=12, weight=ft.FontWeight.W_600, color=C.WHITE,
              max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
            left=0, right=0, bottom=0, padding=ft.padding.only(9, 18, 9, 8),
            gradient=ft.LinearGradient(begin=ft.alignment.top_center,
                                       end=ft.alignment.bottom_center,
                                       colors=list(C.POSTER_SCRIM)))
        children = [poster, scrim] + self._tile_marks(a, running)

        tile = ft.Container(
            ft.Stack(children), width=width, height=height, bgcolor=C.PANEL,
            border=ft.border.all(2, self.ui._accent()) if selected else ft.border.all(1, C.LINE),
            border_radius=12, clip_behavior=ft.ClipBehavior.HARD_EDGE)

        def on_hover(e):
            if selected:
                return
            tile.border = ft.border.all(1, C.LINE_4 if e.data == "true" else C.LINE)
            Wg.safe_update(tile)
        tile.on_hover = on_hover
        return self._tile_gestures(tile, a, ids)

    def _tile_gestures(self, tile, a, ids):
        return ft.GestureDetector(
            tile, mouse_cursor=ft.MouseCursor.CLICK,
            on_tap_down=lambda e, i=a["id"]: self.ui._tile_tap(i, ids, e),
            on_secondary_tap_down=lambda e, ap=a: self.ui.context_menus.app_menu(ap, e))

    def _list(self, apps):
        ids = [a["id"] for a in apps]
        ids_key = hash(tuple(ids))
        rows = [self._list_row(a, ids, ids_key) for a in apps]
        return ft.Container(ft.Column(rows, spacing=6), padding=ft.padding.only(0, 0, 0, 18))

    def _list_row(self, a, ids, ids_key):
        running = a["id"] in self.ui.running
        picked = a["id"] in self.ui.view.sel
        selected = picked or (not self.ui.view.select_mode and a["id"] == self.ui._sel_id)
        cat = self.ui.cat_of(a)
        sig = self._tile_signature(a, ids_key, running, selected, picked, cat)
        self.ui._tiles_used.add(a["id"])
        hit = self.ui._tile_cache.get(a["id"])
        if hit is not None and hit[0] == sig:
            self.ui._tile_cache.move_to_end(a["id"])
            return hit[1]
        lines = [T(a["name"], size=13, weight=ft.FontWeight.W_600, color=C.TEXT)]
        meta = self._tile_meta(a, cat)
        if meta:
            lines.append(T(meta, size=11, color=C.MUTED_2,
                           font_family="monospace" if meta.startswith("Ctrl") else None))
        controls = []
        if self.ui.view.select_mode:
            controls.append(ft.Icon(ft.Icons.CHECK_BOX if picked
                                    else ft.Icons.CHECK_BOX_OUTLINE_BLANK, size=18,
                                    color=self.ui._accent() if picked else C.TEXT_FAINT))
        controls += [self.ui.icon_slot(a, 32, 9, glyph=17),
                     ft.Column(lines, spacing=1, expand=True, tight=True)]
        if running:
            controls.append(ft.Row([Wg.dot(), T(self.ui.running_note(a), size=11,
                                                   color=C.GREEN_TEXT)],
                                   spacing=6, tight=True))
        if a.get("favorite"):
            controls.append(ft.Icon(ft.Icons.STAR, size=15, color=C.STAR))
        controls.append(ft.Container(ft.Icon(ft.Icons.MORE_HORIZ, size=16, color=C.MUTED),
                                     width=30, height=30, border_radius=9,
                                     alignment=ft.alignment.center, tooltip="Меню",
                                     on_click=lambda e, ap=a: self.ui.context_menus.app_menu(ap, None)))
        row = ft.Container(ft.Row(controls, spacing=12,
                                  vertical_alignment=ft.CrossAxisAlignment.CENTER),
                           padding=ft.padding.symmetric(9, 12), border_radius=11,
                           border=ft.border.all(2, self.ui._accent()) if selected
                           else ft.border.all(1, C.LINE),
                           bgcolor=C.SELECTED_BG if selected else C.PANEL)
        if not selected:
            Wg.hoverable(row, C.PANEL, C.SELECTED_BG)
        built = ft.GestureDetector(row,
                                   on_tap_down=lambda e, i=a["id"]: self.ui._tile_tap(i, ids, e),
                                   on_secondary_tap_down=lambda e, ap=a: self.ui.context_menus.app_menu(ap, e))
        self.ui._tile_cache[a["id"]] = (sig, built)
        self.ui._tile_cache.move_to_end(a["id"])
        return built

    def _empty(self, title, text, btn_label, on_click):
        controls = [
            T(title, size=15, weight=ft.FontWeight.W_600, color=C.TEXT_2),
            ft.Container(height=8),
            T(text, size=13, color=C.MUTED_2, text_align=ft.TextAlign.CENTER, width=380),
        ]
        if btn_label:
            controls += [ft.Container(height=18),
                         Wg.primary_btn(btn_label, on_click, self.ui._accent(), self.ui.calm(),
                                       ft.Icons.ADD)]
        return ft.Container(
            ft.Column(controls, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
            alignment=ft.alignment.center, padding=ft.padding.only(0, 80, 0, 40))
