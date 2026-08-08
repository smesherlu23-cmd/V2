from __future__ import annotations

import flet as ft

from ...core import queries
from ...core.text import plu_programs
from .. import colors as C
from .. import widgets as Wg
from ..format import T


def build_triage_screen(ui):
    queue = ui.inbox()
    if not queue:
        return _triage_done(ui)

    item = queue[0]
    total = len(queue)
    done = getattr(ui.triage, "done_count", 0)
    picks = queries.suggest_categories(item, ui.categories())

    head = ft.Container(
        ft.Row([ft.Column([
            T("Разбор", size=16, weight=ft.FontWeight.BOLD, color=C.TEXT),
            T(f"Осталось {total} · разобрано {done}", size=12, color=C.TEXT_DIM),
        ], spacing=4, tight=True, expand=True),
            ft.Container(T("Отложить всё", size=12.5, color=C.MUTED_2),
                         on_click=lambda e: ui.triage.triage_defer_all())],
            spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.padding.only(26, 22, 26, 0))

    bar = ft.Container(
        ft.Row([ft.Container(height=3, border_radius=2, bgcolor=C.ACCENT, expand=max(done, 0) or 1
                             if done else 1, visible=bool(done)),
                ft.Container(height=3, border_radius=2, bgcolor=C.PROGRESS_TRACK, expand=total)],
               spacing=3), padding=ft.padding.only(26, 16, 26, 0))

    chips = []
    for index, cat in enumerate(picks):
        first = index == 0
        row = [T(str(index + 1), size=11, weight=ft.FontWeight.BOLD,
                 color=C.MUTED if first else C.TEXT_FAINT, font_family="monospace"),
               Wg.cat_glyph(cat, size=17, color=C.category_color(cat) if first else C.TEXT_2),
               T(cat["name"], size=13.5, weight=ft.FontWeight.W_600 if first else None,
                 color=C.TEXT if first else C.TEXT_2)]
        if first and not ui.calm():
            row.append(T("похоже", size=11, color=C.MUTED_2))
        chips.append(ft.Container(
            ft.Row(row, spacing=9, tight=True,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            height=44, padding=ft.padding.symmetric(0, 16), border_radius=12,
            bgcolor=C.TRIAGE_PICK_BG if first else None,
            border=ft.border.all(1, C.TRIAGE_PICK_BORDER if first else C.TRIAGE_CHIP_BORDER),
            on_click=lambda e, cid=cat["id"], iid=item["id"]: ui.triage.triage_place(iid, cid)))

    source = queries.SOURCES.get(item.get("source") or "", {}).get("label", "")
    card = ft.Column([
        ft.Container(ui.icon_slot(item, 92, 24, glyph=42, border=C.TRIAGE_SLOT_BORDER),
                     alignment=ft.alignment.center),
        ft.Column([
            T(item["name"], size=22, weight=ft.FontWeight.BOLD, color=C.TEXT,
              text_align=ft.TextAlign.CENTER),
            T(source, size=12, color=C.TEXT_DIM),
        ], spacing=7, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        ft.Container(ft.Row(chips, spacing=9, wrap=True, run_spacing=9,
                            alignment=ft.MainAxisAlignment.CENTER),
                     padding=ft.padding.only(0, 2, 0, 0)),
    ], spacing=20, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER)

    def hint(key, label):
        return ft.Row([ft.Container(T(key, size=10.5, color=C.MUTED, font_family="monospace"),
                                    bgcolor=C.PANEL_2, border=ft.border.all(1, C.LINE),
                                    border_radius=4, padding=ft.padding.symmetric(2, 6)),
                       T(label, size=11.5, color=C.MUTED_2)], spacing=7, tight=True)

    footer = ft.Container(
        ft.Row([hint("1–4", "положить в категорию"), hint("Enter", "взять предложенную"),
                hint("→", "пропустить"), ft.Container(expand=True),
                ft.Container(hint("Del", "не нужно"),
                             on_click=lambda e, iid=item["id"]: ui.triage.triage_drop(iid))],
               spacing=20, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        height=52, bgcolor=C.BG_2, padding=ft.padding.symmetric(0, 26),
        border=ft.border.only(top=ft.BorderSide(1, C.LINE_2)))

    return ft.Column([head, bar,
                      ft.Container(card, expand=True, padding=ft.padding.symmetric(0, 26),
                                   alignment=ft.alignment.center),
                      footer], spacing=0, expand=True)


def _triage_done(ui):
    done = getattr(ui.triage, "done_count", 0)
    text = (f"{done} {plu_programs(done)} лежат по местам. " if done else "")
    return ft.Container(
        ft.Column([
            ft.Container(ft.Icon(ft.Icons.CHECK, size=28, color=C.GREEN),
                         width=64, height=64, border_radius=20, bgcolor=C.DONE_BG,
                         border=ft.border.all(1, C.DONE_BORDER),
                         alignment=ft.alignment.center),
            T("Всё разобрано", size=18, weight=ft.FontWeight.BOLD, color=C.TEXT),
            T(text + "Новое появится здесь само — заходить специально не нужно.",
              size=13, color=C.MUTED_2, width=300, text_align=ft.TextAlign.CENTER),
            ft.Container(ft.Row([
                Wg.primary_btn("К библиотеке", ui.back_to_grid, ui._accent(), ui.calm()),
                Wg.outline_btn("Поискать ещё", ui.open_add),
            ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
                padding=ft.padding.only(0, 8, 0, 0)),
        ], spacing=16, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER),
        expand=True, alignment=ft.alignment.center, padding=ft.padding.all(36))
