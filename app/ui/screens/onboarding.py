from __future__ import annotations

import flet as ft

from .. import colors as C
from .. import widgets as Wg
from ..format import T


def build_onboarding(ui):
    items = ui.onboarding_items()
    scanning = ui.scan.scanning() and not items
    picked = getattr(ui.view, "onboarding_sel", set())

    rows = []
    for suggestion in items:
        app = suggestion["app"]
        key = (app.get("path") or "").lower()
        checked = key in picked
        rows.append(ft.Container(
            ft.Row([
                ft.Icon(ft.Icons.CHECK_BOX if checked else ft.Icons.CHECK_BOX_OUTLINE_BLANK,
                        size=18, color=C.ACCENT if checked else C.MUTED),
                ui.icon_slot(app, 30, 9, glyph=16),
                T(app.get("name") or "", size=13, color=C.TEXT, expand=True, max_lines=1,
                  overflow=ft.TextOverflow.ELLIPSIS),
                T(suggestion["hint"], size=11.5, color=C.MUTED_2),
            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            height=44, padding=ft.padding.symmetric(0, 10), border_radius=10,
            bgcolor=C.PANEL if checked else None,
            border=ft.border.all(1, C.LINE_4) if checked else None,
            on_click=lambda e, k=key: ui.toggle_onboarding(k)))

    if scanning:
        rows = [ft.Container(ft.Row([Wg.spinner(15),
                                     T("Смотрю, что установлено…", size=12.5, color=C.MUTED)],
                                    spacing=10, tight=True),
                             padding=ft.padding.symmetric(18, 0))]
    elif not rows:
        rows = [ft.Container(T("Ничего подходящего не нашлось — добавьте программы вручную.",
                               size=12.5, color=C.MUTED),
                             padding=ft.padding.symmetric(18, 0))]

    card = ft.Container(
        ft.Column([
            T("Отметьте, чем пользуетесь каждый день", size=18, weight=ft.FontWeight.BOLD,
              color=C.TEXT),
            T("Отмеченные сразу попадут в быстрый запуск. Остальное можно добавить когда "
              "угодно.", size=12.5, color=C.MUTED),
            ft.Container(ft.Column(rows, spacing=2, tight=True),
                         padding=ft.padding.only(0, 4, 0, 0)),
            ft.Row([T(f"Отмечено {len(picked)} из {len(items)}" if items else "", size=12,
                      color=C.MUTED_2, expand=True),
                    ft.Container(T("Позже", size=12.5, color=C.MUTED),
                                 padding=ft.padding.symmetric(9, 12),
                                 on_click=lambda e: ui.close_onboarding()),
                    Wg.primary_btn("Добавить и начать", ui.commit_onboarding,
                                  ui._accent(), ui.calm())],
                   spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ], spacing=14, tight=True),
        width=520, bgcolor=C.BG_1, border=ft.border.all(1, C.SLOT_BORDER),
        border_radius=16, padding=ft.padding.all(24),
        shadow=ft.BoxShadow(blur_radius=100, offset=ft.Offset(0, 40), color=C.SHADOW_MENU))
    return ft.Container(card, bgcolor=C.OVERLAY, alignment=ft.alignment.center, expand=True)
