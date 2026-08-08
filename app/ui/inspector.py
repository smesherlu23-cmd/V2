from __future__ import annotations

import flet as ft

from ..core.text import short_ago, time_ago
from . import colors as C
from . import widgets as Wg
from .format import T


def _short_path(path: str) -> str:
    if not path:
        return ""
    if "://" in path:
        return path
    parts = str(path).replace("/", "\\").split("\\")
    tail = "\\".join(parts[-2:]) if len(parts) > 2 else "\\".join(parts)
    return f"…\\{tail}" if len(parts) > 2 else tail


class InspectorPanel:
    def __init__(self, ui):
        self.ui = ui

    def build_inspector(self):
        app = next((a for a in self.ui.apps() if a["id"] == self.ui.view.inspector), None)
        if app is None:
            return None
        running = app["id"] in self.ui.running
        cat = self.ui.cat_of(app)

        status = ft.Row([Wg.dot(), T(self.ui.running_note(app), size=11.5,
                                       color=C.GREEN_TEXT)],
                        spacing=6, tight=True) if running else \
            T(short_ago(app.get("last_launched")) or "ещё не открывали",
              size=11.5, color=C.MUTED_2)
        header = ft.Container(
            ft.Row([self.ui.icon_slot(app, 46, 13, glyph=23),
                    ft.Column([T(app["name"], size=15.5, weight=ft.FontWeight.BOLD,
                                 color=C.TEXT, max_lines=1,
                                 overflow=ft.TextOverflow.ELLIPSIS),
                               status], spacing=5, expand=True, tight=True),
                    ft.Container(ft.Icon(ft.Icons.CLOSE, size=18, color=C.MUTED_2),
                                 on_click=lambda e: self.ui._close_inspector(),
                                 tooltip="Закрыть панель")],
                   spacing=12, vertical_alignment=ft.CrossAxisAlignment.START),
            padding=ft.padding.only(18, 18, 18, 16))

        def square(icon, tooltip, handler, color=C.MUTED):
            return ft.Container(ft.Icon(icon, size=16, color=color), width=38, height=36,
                                border=ft.border.all(1, C.LINE_4), border_radius=9,
                                alignment=ft.alignment.center, tooltip=tooltip,
                                on_click=lambda e: handler())

        actions = ft.Container(
            ft.Row([
                Wg.primary_btn("Переключиться" if running else "Запустить",
                              lambda: self.ui._launch(app["id"]), self.ui._accent(), self.ui.calm(),
                              ft.Icons.SYNC_ALT if running else ft.Icons.PLAY_ARROW,
                              height=36, expand=True),
                square(ft.Icons.STAR if app.get("favorite") else ft.Icons.STAR_BORDER,
                       "В избранное", lambda: self.ui._toggle_fav(app["id"]),
                       C.STAR if app.get("favorite") else C.MUTED),
                square(ft.Icons.FOLDER_OPEN, "Показать в папке",
                       lambda: self.ui._show_in_folder(app["id"])),
                square(ft.Icons.MORE_HORIZ, "Ещё способы запуска",
                       lambda: self.ui.context_menus.launch_more_menu(app, None)),
            ], spacing=8), padding=ft.padding.only(18, 0, 18, 0))

        props = [
            self._insp_row("Категория", self._cat_selector(app, cat)),
            self._insp_row("Быстрый запуск",
                           Wg.toggle(bool(app.get("quick")),
                                    lambda v: self.ui._toggle_quick(app["id"], v),
                                    self.ui._accent()),
                           sub=self._quick_sub(app), always=True),
            self._insp_row("Своя горячая клавиша", self._hotkey_field(app),
                           sub="Нажмите комбинацию" if self.ui.view.capture
                           else "Работает из любого окна"),
            self._insp_row("В наборах", self._set_chips(app)),
        ]
        props.append(ft.Container(height=1, bgcolor=C.LINE_2))
        props.append(self._insp_tech(app))
        placement = ft.Container(ft.Column(props, spacing=12),
                                 padding=ft.padding.only(18, 18, 18, 0))

        footer = ft.Container(
            ft.Row([T("" if self.ui.calm() else "сохраняется само", size=10.5,
                      color=C.MUTED_3, expand=True),
                    Wg.outline_btn("Убрать", lambda: self.ui._remove_apps([app["id"]]),
                                     ft.Icons.DELETE_OUTLINE, danger=True, height=30)],
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.symmetric(14, 18),
            border=ft.border.only(top=ft.BorderSide(1, C.LINE_2)))

        return ft.Container(
            ft.Column([header, actions,
                       ft.Column([placement, self._insp_advanced(app),
                                  ft.Container(height=18)],
                                 spacing=0, expand=True, scroll=ft.ScrollMode.AUTO),
                       footer], spacing=0, expand=True),
            border=ft.border.only(left=ft.BorderSide(1, C.LINE_2)), expand=True)

    def _insp_row(self, label, control, sub=None, always=False):
        left = [T(label, size=12.5, color=C.TEXT_2)]
        if sub and (always or not self.ui.calm()):
            left.append(T(sub, size=11, color=C.MUTED_2))
        return ft.Row([ft.Column(left, spacing=1, tight=True, expand=True), control],
                      spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    def _insp_tech(self, app):
        lines = []
        if app.get("path"):
            lines.append(T(app["path"], size=10.5, color=C.MUTED_2))
        stats = []
        if app.get("launch_count"):
            stats.append(T(f"Запусков: {app['launch_count']}", size=11, color=C.MUTED))
        ago = time_ago(app.get("last_launched"))
        if ago:
            stats.append(T(f"Последний: {ago}", size=11, color=C.MUTED))
        if stats:
            lines.append(ft.Row(stats, spacing=14, wrap=True, run_spacing=4))
        if not lines:
            return ft.Container(height=0)
        return ft.Column(lines, spacing=7, tight=True)

    def _set_chips(self, app):
        members = [rec for rec in self.ui.sets() if app["id"] in rec.get("apps", [])]
        chips = [ft.Container(
            ft.Row([ft.Icon(ft.Icons.LAYERS, size=13, color=C.MUTED),
                    T(rec["name"], size=11.5, color=C.TEXT_2, max_lines=1,
                      overflow=ft.TextOverflow.ELLIPSIS)], spacing=6, tight=True),
            height=26, border_radius=13, bgcolor=C.SET_SLOT_BG,
            border=ft.border.all(1, C.CONTROL), padding=ft.padding.symmetric(0, 9),
            on_click=lambda e, sid=rec["id"]: self.ui._open_set(sid)) for rec in members]
        chips.append(ft.Container(
            ft.Row([ft.Icon(ft.Icons.ADD, size=13, color=C.MUTED_2),
                    T("Ещё" if members else "В набор", size=11.5, color=C.MUTED_2)],
                   spacing=6, tight=True),
            height=26, border_radius=13, border=ft.border.all(1, C.DASHED),
            padding=ft.padding.symmetric(0, 9), tooltip="Добавить в набор",
            on_click=lambda e: self.ui.context_menus.add_to_set_menu(app, e)))
        return ft.Row(chips, spacing=6, wrap=True, run_spacing=6, tight=True)

    def _cat_selector(self, app, cat):
        return ft.Container(
            ft.Row([
                ft.Row([Wg.cat_glyph(cat, size=14) if cat
                        else ft.Icon(ft.Icons.FOLDER, size=14, color=C.MUTED),
                        T(cat["name"] if cat else "Без категории", size=12.5, color=C.TEXT,
                          max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)],
                       spacing=6, tight=True, expand=True),
                ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN, size=14, color=C.MUTED_2),
            ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            width=160, height=32, bgcolor=C.PANEL, border=ft.border.all(1, C.CONTROL),
            border_radius=8, padding=ft.padding.symmetric(0, 10),
            tooltip="Выбрать категорию",
            on_click=lambda e: self.ui.context_menus.category_picker(app, e))

    def _quick_sub(self, app) -> str:
        accel = self.ui._accels.get(app["id"])
        if app.get("quick") and accel:
            return f"Сейчас место {accel.split('+')[-1]}"
        if app.get("quick"):
            return "Свободных мест не осталось"
        return "Появится в ленте сверху"

    def _hotkey_field(self, app):
        explicit = app.get("hotkey")
        label = "нажмите…" if self.ui.view.capture else (explicit or "не задана")
        row = [T(label, size=11.5, font_family="monospace",
                 color=C.TEXT if (explicit or self.ui.view.capture) else C.MUTED_2),
               ft.Icon(ft.Icons.EDIT, size=14, color=C.MUTED_2)]
        field = ft.Container(
            ft.Row(row, spacing=8, tight=True,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            height=32, padding=ft.padding.symmetric(0, 10), bgcolor=C.PANEL,
            border=ft.border.all(1, self.ui._accent() if self.ui.view.capture else C.CONTROL),
            border_radius=8, alignment=ft.alignment.center,
            tooltip="Нажмите комбинацию" if self.ui.view.capture
            else "Своя комбинация, работает из любого окна",
            on_click=lambda e: self.ui._begin_capture())
        if app.get("hotkey") and not self.ui.view.capture:
            return ft.Row([field,
                           ft.Container(ft.Icon(ft.Icons.CLOSE, size=14, color=C.MUTED_2),
                                        tooltip="Убрать комбинацию",
                                        on_click=lambda e: self.ui._set_hotkey(app["id"], None))],
                          spacing=6, tight=True)
        return field

    def _insp_advanced(self, app):
        args_value = " ".join(app.get("args") or []) if isinstance(app.get("args"), list) \
            else str(app.get("args") or "")
        open_now = self.ui.view.adv or bool(args_value) or bool(app.get("run_as_admin")) \
            or bool(app.get("working_dir"))
        head = ft.Container(
            ft.Row([Wg.caps("ПАРАМЕТРЫ ЗАПУСКА"),
                    ft.Container(height=1, bgcolor=C.LINE_2, expand=True),
                    ft.Icon(ft.Icons.EXPAND_LESS if open_now else ft.Icons.EXPAND_MORE,
                            size=16, color=C.TEXT_FAINT)],
                   spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            on_click=lambda e: self.ui._toggle_adv())
        if not open_now:
            return ft.Container(head, padding=ft.padding.only(18, 18, 18, 0))

        args_field = ft.TextField(
            value=args_value, hint_text="не заданы", height=32, text_size=11.5,
            color=C.TEXT, bgcolor=C.PANEL, border_color=C.CONTROL,
            focused_border_color=C.LINE_5, border_radius=8,
            content_padding=ft.padding.symmetric(0, 10), cursor_color=C.TEXT,
            hint_style=ft.TextStyle(color=C.MUTED_2, size=11.5),
            text_style=ft.TextStyle(font_family="mono"), expand=True,
            on_blur=lambda e: self.ui._set_args(app["id"], e.control.value),
            on_submit=lambda e: self.ui._set_args(app["id"], e.control.value))

        workdir = (app.get("working_dir") or "").strip()
        folder = ft.Container(
            ft.Row([T(_short_path(workdir) if workdir else "как у файла", size=11.5,
                      color=C.TEXT_2 if workdir else C.MUTED_2, font_family="monospace",
                      expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Container(ft.Icon(ft.Icons.FOLDER_OPEN, size=15, color=C.MUTED_2),
                                 on_click=lambda e: self.ui._pick_working_dir(app["id"]))],
                   spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            height=32, bgcolor=C.PANEL, border=ft.border.all(1, C.CONTROL), border_radius=8,
            padding=ft.padding.only(10, 0, 6, 0), expand=True)

        proc = (app.get("track_exe") or "").strip()
        proc_box = ft.Container(
            ft.Row([T(proc or "не определён", size=11.5, font_family="monospace",
                      color=C.TEXT if proc else C.MUTED_2, expand=True,
                      max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    T("найден" if proc and app["id"] in self.ui.running else "", size=11,
                      color=C.GREEN)],
                   spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            height=32, bgcolor=C.PANEL, border=ft.border.all(1, C.CONTROL), border_radius=8,
            padding=ft.padding.symmetric(0, 10), expand=True)

        def labelled(label, control):
            return ft.Row([T(label, size=12, color=C.MUTED, width=74), control],
                          spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        return ft.Container(ft.Column([
            head,
            labelled("Аргументы", args_field),
            labelled("Папка", folder),
            labelled("Процесс", proc_box),
            self._insp_row("От администратора",
                           Wg.toggle(bool(app.get("run_as_admin")),
                                    lambda v: self.ui._set_admin(app["id"], v),
                                    self.ui._accent()),
                           sub="Будет запрос UAC"),
        ], spacing=9), padding=ft.padding.only(18, 18, 18, 0))
