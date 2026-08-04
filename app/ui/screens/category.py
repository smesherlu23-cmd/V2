from __future__ import annotations

import flet as ft

from .. import colors as C
from .. import widgets as Wg
from ..format import ICON_PACK, T, cat_icon
from .common import _caps, _field


def build_category_popover(ui, cat):
    color = C.category_color(cat)
    hue, lightness, _sat = C.hex_to_hsl(color)

    name_field = ft.TextField(
        value=cat["name"], border=ft.InputBorder.NONE, filled=False, dense=True,
        text_size=13.5, color=C.TEXT, cursor_color=C.TEXT, expand=True,
        content_padding=ft.padding.symmetric(0, 0),
        text_style=ft.TextStyle(weight=ft.FontWeight.W_600),
        on_blur=lambda e: ui.rename_category(cat["id"], e.control.value),
        on_submit=lambda e: ui.rename_category(cat["id"], e.control.value))

    header = ft.Row([
        ft.Container(Wg.cat_glyph(cat, size=18), width=34, height=34, border_radius=10,
                     bgcolor=C.PANEL_3, border=ft.border.all(1, C.LINE_4),
                     alignment=ft.alignment.center),
        ft.Container(name_field, height=30, bgcolor=C.BG_1,
                     border=ft.border.all(1, C.SLOT_BORDER), border_radius=7,
                     padding=ft.padding.symmetric(0, 9), expand=True),
        ft.Container(ft.Icon(ft.Icons.CLOSE, size=17, color=C.MUTED_2),
                     on_click=lambda e: ui.close_popover()),
    ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    swatches = [ft.Container(
        width=24, height=24, border_radius=7, bgcolor=hexval,
        border=ft.border.all(2, C.ACCENT) if hexval.lower() == color.lower() else None,
        tooltip=hexval.upper(),
        on_click=lambda e, h=hexval: ui.set_category_color(cat["id"], h))
        for hexval in C.CAT_PALETTE]

    hex_box = ft.Container(
        ft.Row([ft.Container(width=14, height=14, border_radius=4, bgcolor=color),
                _field(color.upper(), "#RRGGBB", mono=True, size=12,
                       on_submit=lambda e: ui.set_category_color(
                           cat["id"], C.parse_hex(e.control.value) or color))],
               spacing=7, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        width=104, height=32, bgcolor=C.BG_1, border=ft.border.all(1, C.SLOT_BORDER),
        border_radius=8, padding=ft.padding.symmetric(0, 9))

    def slider_row(label, value, maximum, gradient, on_change):
        return ft.Row([
            T(label, size=10.5, color=C.TEXT_DIM, width=26),
            ft.Container(
                ft.Slider(min=0, max=maximum, value=value, on_change_end=on_change,
                          active_color=C.ACCENT, inactive_color=C.TRANSPARENT,
                          thumb_color=color, height=18, expand=True),
                gradient=ft.LinearGradient(begin=ft.alignment.center_left,
                                           end=ft.alignment.center_right,
                                           colors=list(gradient)),
                border_radius=3, height=18, expand=True,
                padding=ft.padding.symmetric(0, 0)),
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    sliders = ft.Column([
        slider_row("тон", hue, 359, C.HUE_STRIP,
                   lambda e: ui.set_category_color(
                       cat["id"], C.hsl_to_hex(float(e.control.value), lightness))),
        slider_row("ярк.", lightness * 100, 100, (C.BG_1, color, C.WHITE),
                   lambda e: ui.set_category_color(
                       cat["id"], C.hsl_to_hex(hue, float(e.control.value) / 100))),
    ], spacing=5, tight=True, expand=True)

    cells = [ft.Container(
        ft.Icon(cat_icon(name), size=17,
                color=color if name == cat.get("icon") and not cat.get("image") else C.TEXT_2),
        width=34, height=34, border_radius=9,
        bgcolor=C.PANEL_3 if name == cat.get("icon") else C.BG_1,
        border=ft.border.all(2, C.ACCENT) if name == cat.get("icon") and not cat.get("image")
        else ft.border.all(1, C.LINE),
        alignment=ft.alignment.center, tooltip=name,
        on_click=lambda e, n=name: ui.set_category_icon(cat["id"], n)) for name in ICON_PACK]

    image_row = ft.Container(
        ft.Row([ft.Icon(ft.Icons.IMAGE, size=17, color=C.MUTED),
                ft.Column([T("Своя картинка", size=12.5, color=C.TEXT_2),
                           T("PNG или SVG", size=10.5, color=C.TEXT_DIM)],
                          spacing=1, expand=True, tight=True),
                ft.Container(T("Убрать" if cat.get("image") else "Выбрать", size=11.5,
                               color=C.TEXT),
                             border=ft.border.all(1, C.LINE_4), border_radius=7,
                             padding=ft.padding.symmetric(5, 10),
                             on_click=lambda e: (ui.clear_category_image(cat["id"])
                                                 if cat.get("image")
                                                 else ui.pick_category_image(cat["id"])))],
               spacing=9, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        height=44, border=ft.border.all(1, C.LINE_4), border_radius=10,
        padding=ft.padding.symmetric(0, 12), margin=ft.margin.only(top=10))

    footer = ft.Container(
        ft.Row([ft.Container(
            ft.Row([ft.Icon(ft.Icons.DELETE_OUTLINE, size=15, color=C.ERR_TEXT),
                    T("Удалить категорию", size=12, color=C.ERR_TEXT)], spacing=6, tight=True),
            on_click=lambda e: ui._remove_category(cat["id"])),
            ft.Container(expand=True),
            T("" if ui.calm() else "Esc", size=10.5, color=C.MUTED_3,
              font_family="monospace")],
            vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.padding.only(0, 14, 0, 0), margin=ft.margin.only(top=12),
        border=ft.border.only(top=ft.BorderSide(1, C.LINE_2)))

    return ft.Container(
        ft.Column([
            header,
            _caps("ЦВЕТ"),
            ft.Row(swatches, spacing=6, wrap=True, run_spacing=6),
            ft.Row([hex_box, sliders], spacing=10,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Container(height=1, bgcolor=C.LINE_2, margin=ft.margin.symmetric(10, 0)),
            _caps("ИКОНКА"),
            ft.Container(ft.Column([ft.Row(cells, spacing=6, wrap=True, run_spacing=6)],
                                   scroll=ft.ScrollMode.AUTO), height=120),
            image_row,
            footer,
        ], spacing=10, tight=True),
        width=C.POPOVER_W, bgcolor=C.PANEL, border=ft.border.all(1, C.LINE_4),
        border_radius=14, padding=ft.padding.all(16),
        shadow=ft.BoxShadow(blur_radius=60, offset=ft.Offset(0, 24), color=C.SHADOW_MENU))
