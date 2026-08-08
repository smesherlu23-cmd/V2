from __future__ import annotations

import flet as ft

from ...core import queries
from .. import colors as C
from .. import widgets as Wg
from ..format import T
from .common import _caps


def build_palette(ui, rows):
    children = []
    app_rows = [r for r in rows if r["kind"] == "app"]
    set_rows = [r for r in rows if r["kind"] == "set"]

    if app_rows:
        children.append(_group_head("ПРОГРАММЫ", first=True))
        children.append(_palette_list([_palette_app_row(ui, r) for r in app_rows]))
    if set_rows:
        children.append(_group_head("НАБОРЫ", first=not app_rows))
        children.append(_palette_list([_palette_set_row(ui, r) for r in set_rows]))
    if not rows:
        children.append(_palette_empty(ui))

    actions = queries.palette_actions(ui._palette_app())
    if actions:
        children.append(_group_head("ДЕЙСТВИЯ"))
        children.append(ft.Container(
            ft.Column([_palette_action_row(ui, a, i) for i, a in enumerate(actions)],
                      spacing=1, tight=True),
            padding=ft.padding.only(8, 0, 8, 10)))
    return ft.Container(
        ft.Column(children, spacing=0, tight=True),
        width=C.PALETTE_W, bgcolor=C.PALETTE_BG,
        border=ft.border.all(1, C.PALETTE_BORDER), border_radius=14,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        shadow=ft.BoxShadow(blur_radius=70, offset=ft.Offset(0, 30),
                            color=C.SHADOW_PALETTE))


def _group_head(label, first: bool = False):
    return ft.Container(_caps(label),
                        padding=ft.padding.only(16, 12 if first else 14, 16, 6))


def _palette_list(rows):
    return ft.Container(ft.Column(rows, spacing=1, tight=True),
                        padding=ft.padding.symmetric(0, 8))


def _palette_row(ui, index: int, plate, lines, right, on_click, height=48):
    active = (ui.view.palette_index == index
              and ui.view.palette_focus == "results")
    controls = [plate, ft.Column(lines, spacing=1, expand=True, tight=True)]
    if right is not None:
        controls.append(right)
    row = ft.Container(
        ft.Row(controls, spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        height=height, padding=ft.padding.symmetric(0, 12), border_radius=10,
        bgcolor=C.PALETTE_ROW if active else None,
        on_click=lambda e: on_click())
    row.on_hover = lambda e, i=index: ui.palette_hover(i, e)
    return row


def _palette_app_row(ui, row):
    app = row["app"]
    active = (ui.view.palette_index == row["index"]
              and ui.view.palette_focus == "results")
    right = Wg.key_chip("Enter", ui._accent(), bright=True) if active else None
    sub = queries.app_palette_sub(row, ui.window_count(app))
    lines = [T(spans=[
        ft.TextSpan(text, ft.TextStyle(bgcolor=C.MATCH_BG) if hit else None)
        for text, hit in queries.match_spans(app["name"], ui.view.query)
    ], size=14, weight=ft.FontWeight.W_500, color=C.WHITE if active else C.TEXT,
        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)]
    if sub:
        lines.append(T(sub, size=11, color=C.MUTED if active else C.MUTED_2,
                       max_lines=1, overflow=ft.TextOverflow.ELLIPSIS))
    plate = ui.icon_slot(app, 32, 9, glyph=17,
                         border=C.SLOT_BORDER_SEL if active else None,
                         glyph_color=C.SLOT_GLYPH_SEL if active else None)
    return _palette_row(ui, row["index"], plate, lines, right,
                        lambda r=row: ui.palette_click(r))


def _palette_set_row(ui, row):
    rec = row["set"]
    active = (ui.view.palette_index == row["index"]
              and ui.view.palette_focus == "results")
    right = Wg.key_chip("Enter", ui._accent(), bright=True) if active else None
    lines = [T(rec["name"], size=14, weight=ft.FontWeight.W_500,
               color=C.WHITE if active else C.TEXT, max_lines=1,
               overflow=ft.TextOverflow.ELLIPSIS)]
    lines.append(T(queries.set_palette_sub(rec, row["members"]), size=11,
                   color=C.MUTED if active else C.MUTED_2, max_lines=1,
                   overflow=ft.TextOverflow.ELLIPSIS))
    return _palette_row(ui, row["index"], Wg.set_slot(32, 9, 16), lines, right,
                        lambda r=row: ui.palette_click(r))


def _palette_action_row(ui, action, index):
    active = ui.view.palette_focus == "actions" and ui.view.palette_index == index
    controls = [ft.Container(ft.Icon(action["icon"], size=17, color=C.SLOT_GLYPH),
                             width=32, alignment=ft.alignment.center),
                T(action["label"], size=13.5, color=C.WHITE if active else C.TEXT_2,
                  expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)]
    row = ft.Container(
        ft.Row(controls, spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        height=40, padding=ft.padding.symmetric(0, 12), border_radius=10,
        bgcolor=C.PALETTE_ROW if active else None,
        on_click=lambda e, k=action["key"]: ui.run_palette_action(k))
    if not active:
        Wg.hoverable(row, None, C.PALETTE_ROW)
    return row


def _palette_empty(ui):
    return ft.Container(
        ft.Row([T("Ничего не найдено", size=13.5, color=C.MUTED, expand=True),
                Wg.link_btn("Найти на диске", ui.open_add)],
               vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.padding.only(16, 14, 16, 16))
