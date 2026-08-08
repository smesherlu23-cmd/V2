from __future__ import annotations

import flet as ft

from .. import colors as C
from .. import widgets as Wg
from ..format import T


def build_bulk_bar(ui):
    ids = list(ui.view.sel)

    def action(label, icon, on_click, icon_color=C.TEXT_2, arrow=False, plain=False,
               color=C.TEXT):
        row = [ft.Icon(icon, size=15, color=icon_color),
               T(label, size=12.5, weight=ft.FontWeight.W_500, color=color)]
        if arrow:
            row.append(ft.Icon(ft.Icons.KEYBOARD_ARROW_UP, size=14, color=C.SLOT_GLYPH))
        btn = ft.Container(
            ft.Row(row, spacing=7, tight=True), height=36,
            padding=ft.padding.symmetric(0, 12), border_radius=9,
            bgcolor=None if plain else C.BAR_BTN, alignment=ft.alignment.center,
            on_click=lambda e: on_click())
        return Wg.hoverable(btn, None if plain else C.BAR_BTN, C.PANEL_ACTIVE)

    def divider():
        return ft.Container(width=1, height=20, bgcolor=C.LINE_4,
                            margin=ft.margin.symmetric(0, 4))

    cancel = ft.Container(
        T("Отмена", size=12.5, weight=ft.FontWeight.W_500, color=C.MUTED),
        height=36, padding=ft.padding.symmetric(0, 12), border_radius=9,
        alignment=ft.alignment.center, on_click=lambda e: ui.toggle_select_mode())
    Wg.hoverable(cancel, None, C.BAR_BTN)

    in_hidden = ui.view.filter == "hidden"
    return ft.Container(
        ft.Row([
            T(f"Выбрано {len(ids)}", size=13, weight=ft.FontWeight.W_600, color=C.WHITE),
            divider(),
            action("Категория", ft.Icons.FOLDER, lambda: ui.context_menus.bulk_menu("cat"), arrow=True),
            action("В набор", ft.Icons.LAYERS, lambda: ui.context_menus.bulk_menu("set"), arrow=True),
            action("В избранное", ft.Icons.STAR, lambda: ui._bulk_favorite(ids),
                   icon_color=C.STAR),
            action("Показать" if in_hidden else "Скрыть",
                   ft.Icons.VISIBILITY if in_hidden else ft.Icons.VISIBILITY_OFF,
                   lambda: ui._hide_apps(ids, not in_hidden)),
            action("Убрать", ft.Icons.DELETE_OUTLINE, lambda: ui._remove_apps(ids),
                   icon_color=C.ERR_TEXT, color=C.ERR_TEXT, plain=True),
            divider(),
            cancel,
        ], spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        height=56, bgcolor=C.BAR_BG, border=ft.border.all(1, C.BAR_BORDER),
        border_radius=14, padding=ft.padding.only(16, 0, 10, 0),
        shadow=ft.BoxShadow(blur_radius=44, offset=ft.Offset(0, 18), color=C.SHADOW_BAR))
