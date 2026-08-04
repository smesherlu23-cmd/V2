from __future__ import annotations

import flet as ft

from . import colors as C
from .format import T, cat_icon
from .images import icon_image, is_launcher_art


def hoverable(container: ft.Container, normal, hover) -> ft.Container:
    def on_hover(e):
        container.bgcolor = hover if e.data == "true" else normal
        container.update()
    container.bgcolor = normal
    container.on_hover = on_hover
    return container


def caps(text):
    return T(text, size=10.5, weight=ft.FontWeight.W_600, color=C.MUTED_2,
             style=ft.TextStyle(letter_spacing=0.85))


def key_chip(label, accent, bright=False):
    return ft.Container(
        T(label, size=10.5, weight=ft.FontWeight.W_600 if bright else None,
          color=C.ON_ACCENT if bright else C.SLOT_GLYPH, font_family="monospace"),
        bgcolor=accent if bright else C.PANEL_3,
        border=None if bright else ft.border.all(1, C.CONTROL),
        border_radius=5, padding=ft.padding.symmetric(3, 7))


def toggle(value: bool, on_toggle, accent):
    knob = ft.Container(width=14, height=14, border_radius=7,
                        bgcolor=C.ON_ACCENT if value else C.MUTED_2)
    return ft.Container(
        ft.Row([knob], alignment=ft.MainAxisAlignment.END if value
               else ft.MainAxisAlignment.START),
        width=34, height=19, border_radius=10, padding=ft.padding.all(2.5),
        bgcolor=accent if value else C.LINE_4,
        on_click=lambda e: on_toggle(not value),
        animate=ft.Animation(C.ANIM_FAST, ft.AnimationCurve.EASE_OUT))


def primary_btn(label, on_click, accent, calm, icon=None, height=36, expand=False,
                hint: str = ""):
    row = [T(label, size=13 if height >= 38 else 12.5, weight=ft.FontWeight.W_600,
             color=C.ON_ACCENT)]
    if icon:
        row.insert(0, ft.Icon(icon, size=15, color=C.ON_ACCENT))
    if hint and not calm:
        row.append(T(hint, size=10.5, color=C.ON_ACCENT, opacity=0.55,
                     font_family="monospace"))
    btn = ft.Container(
        ft.Row(row, spacing=7, tight=True, alignment=ft.MainAxisAlignment.CENTER),
        height=height, padding=ft.padding.symmetric(0, 14), bgcolor=accent,
        border_radius=9, alignment=ft.alignment.center, expand=expand,
        on_click=lambda e: on_click())
    return hoverable(btn, accent, C.WHITE)


def outline_btn(label, on_click, icon=None, danger=False, height=34,
                active=False, icon_color=None, weight=None):
    color = C.ERR_TEXT if danger else (C.TEXT if active else C.TEXT_2)
    row = [T(label, size=12.5,
             weight=weight or (ft.FontWeight.W_600 if danger or active
                               else ft.FontWeight.W_500), color=color)]
    if icon:
        row.insert(0, ft.Icon(icon, size=14,
                              color=C.ERR_TEXT if danger
                              else (icon_color or (C.TEXT if active else C.MUTED))))
    btn = ft.Container(
        ft.Row(row, spacing=7, tight=True, alignment=ft.MainAxisAlignment.CENTER),
        height=height, padding=ft.padding.symmetric(0, 12),
        bgcolor=C.PANEL_ACTIVE if active else None,
        border=ft.border.all(1, C.ERR_BORDER if danger
                             else (C.LINE_5 if active else C.CONTROL)),
        border_radius=9, alignment=ft.alignment.center,
        on_click=lambda e: on_click())
    return btn if active else hoverable(btn, None, C.SELECTED_BG)


def link_btn(label, on_click):
    return ft.Container(
        T(label, size=12.5, weight=ft.FontWeight.W_600, color=C.TEXT),
        border=ft.border.only(bottom=ft.BorderSide(1, C.TEXT_FAINT)),
        padding=ft.padding.only(0, 0, 0, 2), on_click=lambda e: on_click())


def spinner(size=38):
    return ft.ProgressRing(width=size, height=size, stroke_width=2.5,
                           color=C.TEXT, bgcolor=C.CONTROL)


def set_slot(size: int, radius: int, glyph: int, muted=False):
    return ft.Container(
        ft.Icon(ft.Icons.LAYERS, size=glyph, color=C.TEXT_FAINT if muted else C.MUTED),
        width=size, height=size, border_radius=radius, bgcolor=C.SET_SLOT_BG,
        border=ft.border.all(1, C.SET_SLOT_BORDER if muted else C.CONTROL),
        alignment=ft.alignment.center)


def dot(size=6, color=C.GREEN):
    return ft.Container(width=size, height=size, border_radius=4, bgcolor=color)


def win_btn(icon_name, tooltip, handler, danger=False):
    c = ft.Container(
        ft.Icon(icon_name, size=14, color=C.MUTED),
        width=40, height=32, border_radius=6, alignment=ft.alignment.center,
        on_click=lambda e: handler(),
    )

    def on_hover(e):
        if e.data == "true":
            c.bgcolor = C.DANGER if danger else C.PANEL_3
            c.content.color = C.WHITE if danger else C.TEXT
        else:
            c.bgcolor = None
            c.content.color = C.MUTED
        c.update()
    c.on_hover = on_hover
    c.tooltip = tooltip
    return c


def cat_glyph_name(cat) -> str:
    return (cat or {}).get("icon") or "folder"


def cat_glyph(cat, size=19, color=None):
    col = color or (C.category_color(cat) if cat else C.MUTED)
    if cat:
        custom = icon_image(cat.get("image"), width=size + 3, height=size + 3,
                            fit=ft.ImageFit.CONTAIN)
        if custom is not None:
            return custom
    return ft.Icon(cat_icon(cat_glyph_name(cat)), size=size, color=col)


def icon_slot(app, size: int, radius: int, glyph: int | None = None,
              border=None, glyph_color=None, bgcolor=None, cat=None,
              source_glyph: str = "folder"):
    fit = ft.ImageFit.COVER if is_launcher_art(app) else ft.ImageFit.CONTAIN
    inner = icon_image(app.get("icon"), width=size - 8, height=size - 8, fit=fit)
    if inner is None:
        name = cat_glyph_name(cat) if cat else source_glyph
        inner = ft.Icon(cat_icon(name), size=glyph or round(size * 0.46),
                        color=glyph_color or C.SLOT_GLYPH)
    return ft.Container(
        inner, width=size, height=size, border_radius=radius,
        bgcolor=bgcolor or C.SLOT_BG,
        border=ft.border.all(1, border or C.SLOT_BORDER), alignment=ft.alignment.center,
        clip_behavior=ft.ClipBehavior.HARD_EDGE)
