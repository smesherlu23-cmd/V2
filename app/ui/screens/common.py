from __future__ import annotations

import flet as ft

from .. import colors as C
from ..format import T


def _caps(text):
    return T(text, size=10.5, weight=ft.FontWeight.W_600, color=C.MUTED_2,
             style=ft.TextStyle(letter_spacing=0.85))


def _screen_header(title, subtitle, on_close, extra=None):
    right = list(extra or [])
    right.append(ft.Container(ft.Icon(ft.Icons.CLOSE, size=20, color=C.MUTED_2),
                              width=32, height=32, alignment=ft.alignment.center,
                              on_click=lambda e: on_close(), tooltip="Закрыть"))
    lines = [T(title, size=19, weight=ft.FontWeight.BOLD, color=C.TEXT)]
    if subtitle:
        lines.append(T(subtitle, size=12.5, color=C.MUTED_2))
    return ft.Container(
        ft.Row([ft.Column(lines, spacing=4, expand=True, tight=True)] + right,
               spacing=16, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.padding.only(24, 20, 24, 16),
        border=ft.border.only(bottom=ft.BorderSide(1, C.LINE_2)))


def _field(value, hint, on_change=None, on_submit=None, mono=False, size=13):
    return ft.TextField(
        value=value or "", hint_text=hint, border=ft.InputBorder.NONE, filled=False,
        dense=True, text_size=size, color=C.TEXT, cursor_color=C.TEXT, expand=True,
        hint_style=ft.TextStyle(color=C.MUTED_2, size=size),
        text_style=ft.TextStyle(font_family="mono") if mono else None,
        content_padding=ft.padding.symmetric(0, 0),
        on_change=on_change, on_submit=on_submit)
