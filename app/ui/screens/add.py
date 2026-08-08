from __future__ import annotations

import flet as ft

from ...core.text import plu_programs
from .. import colors as C
from .. import widgets as Wg
from ..format import T, cat_icon
from .common import _field, _screen_header


def _add_state(ui):
    state = ui._add_ui
    if state is not None:
        return state
    state = {"root": ft.Column([], spacing=0, expand=True)}
    ui._add_ui = state
    return state


def build_add_screen(ui):
    state = _add_state(ui)
    root = state["root"]
    body = _scanning(ui) if ui.scan.scanning() else _found_list(ui, state)
    root.controls = [_add_header(ui), _add_search(ui, state), body, _add_footer(ui)]
    return root


def _add_header(ui):
    groups = [] if ui.scan.scanning() else ui.scan.found_groups()
    total = sum(g["total"] for g in groups)
    fresh = sum(g["new"] for g in groups)
    if ui.scan.scanning():
        subtitle = "Смотрим, что установлено"
    elif total:
        subtitle = f"{total} {plu_programs(total)} на компьютере, {fresh} из них новые"
    else:
        subtitle = "Установленных программ не нашлось"

    rescan = ft.Container(
        ft.Row([Wg.spinner(15) if ui.scan.scanning()
                else ft.Icon(ft.Icons.REFRESH, size=15, color=C.MUTED),
                T("Сканировать снова", size=12.5, color=C.TEXT)],
               spacing=7, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        height=34, padding=ft.padding.symmetric(0, 12),
        border=ft.border.all(1, C.LINE_4), border_radius=8,
        alignment=ft.alignment.center,
        on_click=None if ui.scan.scanning() else (lambda e: ui.scan.start_scan(force=True)))
    return _screen_header("Найти и добавить", subtitle, ui.back_to_grid, extra=[rescan])


def _add_search_field(ui, state):
    field = state.get("search_field")
    if field is None:
        field = _field(ui.view.add_query, "Название программы",
                       on_change=lambda e: ui.scan.set_add_query(e.control.value))
        state["search_field"] = field
    elif not ui.view.add_query and field.value:
        field.value = ""
    return field


def _add_path_field(ui, state):
    field = state.get("path_field")
    if field is None:
        field = _field(ui.view.manual_path,
                       r"Или вставьте путь: C:\Program Files\…\app.exe",
                       on_change=lambda e: ui.scan.set_manual_path(e.control.value),
                       on_submit=lambda e: ui.scan.add_manual_path(e.control.value),
                       mono=True, size=11.5)
        state["path_field"] = field
    elif not ui.view.manual_path and field.value:
        field.value = ""
    return field


def _add_search_container(ui, state):
    box = state.get("search_box")
    if box is not None:
        return box
    box = ft.Container(
        ft.Row([ft.Icon(ft.Icons.SEARCH, size=15, color=C.MUTED_2),
                _add_search_field(ui, state)],
               spacing=9, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        height=36, bgcolor=C.PANEL, border=ft.border.all(1, C.LINE), border_radius=9,
        padding=ft.padding.symmetric(0, 12), expand=True)
    state["search_box"] = box
    return box


def _add_path_container(ui, state):
    box = state.get("path_box")
    if box is not None:
        return box
    box = ft.Container(
        ft.Row([ft.Icon(ft.Icons.LINK, size=15, color=C.MUTED_2),
                _add_path_field(ui, state)],
               spacing=9, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        height=36, bgcolor=C.SET_BG, border=ft.border.all(1, C.LINE_4), border_radius=9,
        padding=ft.padding.symmetric(0, 12), expand=True)
    state["path_box"] = box
    return box


def _add_search(ui, state):
    holder = state.get("search_col")
    if holder is None:
        holder = ft.Column([], spacing=0, tight=True)
        state["search_col"] = holder
    if ui.scan.scanning():
        holder.controls = []
        return holder

    _add_search_field(ui, state)
    _add_path_field(ui, state)

    only_new = ft.Container(
        ft.Row([T("Только новые", size=12.5, color=C.TEXT),
                Wg.toggle(ui.view.only_new, lambda v: ui.scan.toggle_only_new(), ui._accent())],
               spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        height=36, padding=ft.padding.symmetric(0, 12),
        border=ft.border.all(1, C.LINE), border_radius=9,
        on_click=lambda e: ui.scan.toggle_only_new())

    search_row = state.get("search_row")
    if search_row is None:
        search_row = ft.Row([], spacing=10)
        state["search_row"] = search_row
        state["search_row_holder"] = ft.Container(
            search_row, padding=ft.padding.only(24, 14, 24, 6))
    search_row.controls = [_add_search_container(ui, state), only_new]

    path_row = state.get("path_row")
    if path_row is None:
        path_row = ft.Row([], spacing=10)
        state["path_row"] = path_row
        state["path_row_holder"] = ft.Container(
            path_row, padding=ft.padding.only(24, 0, 24, 12))
    path_row.controls = [
        _add_path_container(ui, state),
        Wg.outline_btn("Обзор", ui.scan.pick_file, ft.Icons.FOLDER_OPEN),
        Wg.outline_btn("Добавить путь", ui.scan.add_manual_path),
    ]

    holder.controls = [state["search_row_holder"], state["path_row_holder"]]
    return holder


def _scanning(ui):
    return ft.Container(
        ft.Column([Wg.spinner(38), T("Сканирование", size=15, color=C.TEXT_2)],
                  spacing=22, tight=True,
                  horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                  alignment=ft.MainAxisAlignment.CENTER),
        expand=True, alignment=ft.alignment.center)


def _found_list(ui, state):
    groups = ui.scan.found_groups()
    rows = [_inline_error(ui, err) for err in ui.scan.scan_errors()]
    if not groups:
        rows.append(_add_empty(ui))
    for group in groups:
        rows.append(_add_group(ui, group))

    col = state.get("rows_col")
    if col is None:
        col = ft.Column(rows, spacing=2, scroll=ft.ScrollMode.AUTO, expand=True)
        state["rows_col"] = col
        holder = ft.Container(col, expand=True, padding=ft.padding.only(24, 0, 24, 8))
        state["rows_holder"] = holder
    else:
        col.controls = rows
    return state["rows_holder"]


def _inline_error(ui, err):
    return ft.Container(
        ft.Row([ft.Icon(ft.Icons.ERROR_OUTLINE, size=16, color=C.DANGER),
                ft.Column([T(f"{err.get('label') or 'Источник'} не отдал список программ",
                             size=13, color=C.TEXT),
                           T("Остальные источники прочитались", size=11.5, color=C.MUTED)],
                          spacing=3, expand=True, tight=True),
                Wg.link_btn("Повторить", lambda: ui.scan.start_scan(force=True)),
                ft.Container(T("Скрыть", size=12.5, color=C.MUTED_2),
                             on_click=lambda e: ui.scan.dismiss_scan_errors())],
               spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor=C.ERR_BG, border=ft.border.all(1, C.ERR_BORDER), border_radius=12,
        padding=ft.padding.symmetric(13, 16), margin=ft.margin.only(bottom=8))


def _add_empty(ui):
    only_new = ui.view.only_new
    return ft.Container(
        ft.Column([
            T("Новых программ не нашлось" if only_new else "Ничего не нашлось",
              size=16, weight=ft.FontWeight.BOLD, color=C.TEXT),
            T("Всё установленное уже в библиотеке." if only_new
              else "Автоматический поиск ничего не дал — программу можно указать файлом "
                   "или вставить путь выше.", size=12.5, color=C.MUTED),
            ft.Container(ft.Row([
                Wg.outline_btn("Показать все найденные" if only_new else "Повторить поиск",
                               ui.scan.toggle_only_new if only_new
                               else (lambda: ui.scan.start_scan(force=True))),
                Wg.outline_btn("Выбрать файл", ui.scan.pick_file, ft.Icons.FOLDER_OPEN),
            ], spacing=8), padding=ft.padding.only(0, 6, 0, 0)),
        ], spacing=10, tight=True), width=460, padding=ft.padding.only(0, 30, 0, 0))


def _add_group(ui, group):
    keys = [r["key"] for r in group["rows"] if r["is_new"]]
    picked = [k for k in keys if k in ui.view.add_sel]
    if keys and len(picked) == len(keys):
        box = ft.Icons.CHECK_BOX
        box_color = C.ACCENT
    elif picked:
        box = ft.Icons.INDETERMINATE_CHECK_BOX
        box_color = C.MUTED
    else:
        box = ft.Icons.CHECK_BOX_OUTLINE_BLANK
        box_color = C.MUTED

    head = [ft.Icon(box, size=18, color=box_color),
            ft.Icon(cat_icon(group["icon"]), size=16, color=C.MUTED_2),
            T(group["label"], size=12.5, weight=ft.FontWeight.W_600, color=C.TEXT)]
    head.append(ft.Container(height=1, bgcolor=C.LINE_2, expand=True))

    rows = [ft.Container(ft.Row(head, spacing=10,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER),
                         height=36, on_click=lambda e, g=group: ui.scan.toggle_add_group(g))]
    rows += [_add_row(ui, row) for row in group["rows"]]
    return ft.Container(ft.Column(rows, spacing=2), padding=ft.padding.only(0, 0, 0, 8))


def _add_row(ui, row):
    checked = row["key"] in ui.view.add_sel
    if not row["is_new"]:
        box = ft.Icon(ft.Icons.CHECK_CIRCLE, size=18, color=C.GREEN)
    else:
        box = ft.Icon(ft.Icons.CHECK_BOX if checked else ft.Icons.CHECK_BOX_OUTLINE_BLANK,
                      size=18, color=C.ACCENT if checked else C.MUTED)

    item = row["item"]

    controls = [box, ui.icon_slot(item, 30, 8, glyph=16),
                T(row["name"], size=13, weight=ft.FontWeight.W_600, color=C.TEXT,
                  max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True)]

    if row["is_new"]:
        cat_id = ui.scan.add_category_for(row)
        cat = next((c for c in ui.categories() if c["id"] == cat_id), None)
        controls.append(ft.Container(
            ft.Row([Wg.cat_glyph(cat, size=13) if cat
                    else T("Категория", size=11.5, color=C.MUTED_2),
                    T(cat["name"], size=11.5, color=C.TEXT_2) if cat else ft.Container(),
                    ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN, size=13, color=C.MUTED_2)],
                   spacing=6, tight=True),
            height=28, padding=ft.padding.symmetric(0, 10),
            bgcolor=C.PANEL_3 if cat else None,
            border=ft.border.all(1, C.LINE if cat else C.LINE_4), border_radius=7,
            tooltip="Другая категория",
            on_click=lambda e, r=row: ui.scan.cycle_add_category(r)))

    return ft.Container(
        ft.Row(controls, spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        height=46, padding=ft.padding.symmetric(0, 12), border_radius=10,
        bgcolor=C.PANEL if checked else None,
        border=ft.border.all(1, C.LINE_5) if checked else None,
        opacity=0.45 if not row["is_new"] else 1,
        on_click=lambda e, r=row: ui.scan.toggle_add_row(r))


def _add_footer(ui):
    count = len(ui.view.add_sel)
    left = [T(f"Выбрано {count}" if count else "Ничего не выбрано", size=13,
              weight=ft.FontWeight.W_600, color=C.TEXT)]
    add_label = f"Добавить {count}" if count else "Добавить"
    add_row = [T(add_label, size=13, weight=ft.FontWeight.W_600, color=C.ON_ACCENT)]
    return ft.Container(
        ft.Row(left + [
            ft.Container(expand=True),
            Wg.outline_btn("Отложить в разбор", ui.scan.defer_add, ft.Icons.INBOX),
            ft.Container(ft.Row(add_row, spacing=8, tight=True), height=36,
                         padding=ft.padding.symmetric(0, 16), bgcolor=ui._accent(),
                         border_radius=9, alignment=ft.alignment.center,
                         on_click=lambda e: ui.scan.commit_add()),
        ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        height=64, bgcolor=C.BG_2, padding=ft.padding.symmetric(0, 24),
        border=ft.border.only(top=ft.BorderSide(1, C.LINE_2)))
