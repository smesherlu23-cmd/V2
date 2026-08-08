from __future__ import annotations

import flet as ft

from ...core import layout as L
from ...core.text import plu_programs
from .. import colors as C
from .. import widgets as Wg
from ..format import T
from .common import _caps


def build_set_screen(ui, rec):
    return ft.Column([ft.Container(
        ft.Column([_set_header(ui, rec),
                   ft.Row([_layout_column(ui, rec), _order_column(ui, rec)],
                          spacing=20, vertical_alignment=ft.CrossAxisAlignment.START)],
                  spacing=20, tight=True),
        padding=ft.padding.symmetric(22, 26))],
        spacing=0, expand=True, scroll=ft.ScrollMode.AUTO)


def _set_header(ui, rec):
    accel = ui._set_accels.get(rec["id"])
    name = ft.TextField(
        value=rec["name"], border=ft.InputBorder.NONE, filled=False, dense=True,
        text_size=20, color=C.TEXT, cursor_color=C.TEXT,
        content_padding=ft.padding.symmetric(0, 0),
        text_style=ft.TextStyle(weight=ft.FontWeight.BOLD, font_family="Inter Bold"),
        on_blur=lambda e: ui.set_ops.rename_set(rec["id"], e.control.value),
        on_submit=lambda e: ui.set_ops.rename_set(rec["id"], e.control.value))
    count = len(rec["items"])
    meta = [T(f"{count} {plu_programs(count)}", size=12, color=C.MUTED_2)]
    if accel:
        meta += [_meta_divider(),
                 ft.Container(T(accel, size=11.5, color=C.MUTED, font_family="monospace"),
                              tooltip="Открывает набор из любой программы")]
    meta += [_meta_divider(),
             ft.Container(T(f"Монитор {rec['monitor'] + 1}", size=12, color=C.MUTED_2),
                          tooltip="Куда расставлять окна",
                          on_click=lambda e: ui.context_menus.monitor_menu(rec, e))]
    right = [Wg.outline_btn("Снять с текущих окон",
                            lambda: ui.set_ops.capture_set_layout(rec["id"]), ft.Icons.SAVE,
                            height=38),
             Wg.primary_btn("Запустить набор", lambda: ui.set_ops.launch_set(rec["id"]),
                           ui._accent(), ft.Icons.PLAY_ARROW, height=38)]
    return ft.Row([
        Wg.set_slot(46, 13, 22),
        ft.Column([ft.Container(name, height=28),
                   ft.Row(meta, spacing=12, tight=True,
                          vertical_alignment=ft.CrossAxisAlignment.CENTER)],
                  spacing=5, expand=True, tight=True),
    ] + right, spacing=14, vertical_alignment=ft.CrossAxisAlignment.START)


def _meta_divider():
    return ft.Container(width=1, height=11, bgcolor=C.CONTROL)


def _layout_column(ui, rec):
    head = ft.Row([_caps("РАСКЛАДКА"),
                   ft.Container(height=1, bgcolor=C.LINE_2, expand=True)],
                  spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)
    panel = ft.Container(
        ft.Column([_canvas(ui, rec), _layout_note(ui, rec)], spacing=10, tight=True),
        bgcolor=C.BG_0, border=ft.border.all(1, C.SET_BORDER), border_radius=12,
        padding=ft.padding.all(16))
    presets = ft.Row([_preset_btn(ui, rec, key) for key in L.PRESETS],
                     spacing=8, wrap=True, run_spacing=8)
    return ft.Column([head, panel, presets], spacing=10, tight=True, expand=True)


def _canvas_width(ui) -> float:
    inner = ui._content_width() - 26 * 2 - 20 - C.SET_SIDE_W
    return max(240.0, inner - 2 - 32 - 2 - 16)


def _canvas(ui, rec):
    conf = rec["layout"]
    cw, ch = _canvas_width(ui), C.CANVAS_H - 2 - 16
    children = []
    for entry in rec["items"]:
        rect = L.rect_for(entry, conf["preset"], conf["split"], conf["vsplit"])
        if rect is None:
            continue
        app = next((a for a in ui.apps() if a["id"] == entry["app_id"]), None)
        if app is None:
            continue
        x, y, w, h = rect
        children.append(ft.Container(
            ft.Column([ft.Row([Wg.cat_glyph(ui.cat_of(app), size=15,
                                             color=C.SLOT_GLYPH_SEL),
                               T(app["name"], size=12, weight=ft.FontWeight.W_600,
                                 color=C.TEXT, max_lines=1,
                                 overflow=ft.TextOverflow.ELLIPSIS, expand=True)],
                              spacing=7),
                       T(L.slot_label(conf["preset"], entry.get("slot"), conf["split"])
                         if entry.get("slot") is not None else "своё место",
                         size=10.5, color=C.MUTED_2, max_lines=1,
                         overflow=ft.TextOverflow.ELLIPSIS)],
                      spacing=6, tight=True),
            left=x * cw + 4, top=y * ch + 4,
            width=max(40.0, w * cw - 8), height=max(34.0, h * ch - 8),
            bgcolor=C.WIN_BG, border=ft.border.all(1.5, C.WIN_BORDER), border_radius=6,
            padding=ft.padding.all(10), clip_behavior=ft.ClipBehavior.HARD_EDGE))
    if not children:
        children.append(ft.Container(
            T("Ни одна программа не занимает места — выберите пресет ниже", size=11.5,
              color=C.MUTED_2, text_align=ft.TextAlign.CENTER),
            left=0, top=ch / 2 - 10, width=cw, alignment=ft.alignment.center))
    children += _split_handles(ui, rec, cw, ch)
    return ft.Container(ft.Stack(children, width=cw, height=ch),
                        height=C.CANVAS_H, bgcolor=C.CANVAS_BG,
                        border=ft.border.all(1, C.CONTROL), border_radius=8,
                        padding=ft.padding.all(8))


def _split_handles(ui, rec, cw, ch):
    conf = rec["layout"]
    if conf["preset"] not in L.SPLIT_PRESETS:
        return []
    handles = [_handle(ui, rec, "split", conf["split"] * cw - 4, 0, 8, ch, cw,
                       ft.MouseCursor.RESIZE_LEFT_RIGHT)]
    if conf["preset"] in ("6040", "grid4"):
        left = conf["split"] * cw if conf["preset"] == "6040" else 0
        width = cw - left
        handles.append(_handle(ui, rec, "vsplit", left, conf["vsplit"] * ch - 4,
                               width, 8, ch, ft.MouseCursor.RESIZE_UP_DOWN))
    return handles


def _handle(ui, rec, key, left, top, width, height, span, cursor):
    moved = {"by": 0.0}

    def on_update(e):
        moved["by"] += (e.delta_x if key == "split" else e.delta_y) or 0

    def on_end(e):
        if not moved["by"]:
            return
        current = rec["layout"][key]
        ui.set_ops.set_layout_split(rec["id"], key,
                            L.clamp(current + moved["by"] / max(1.0, span),
                                    L.MIN_SPLIT, L.MAX_SPLIT))
        moved["by"] = 0.0

    return ft.GestureDetector(
        ft.Container(width=width, height=height, border_radius=4),
        left=left, top=top, mouse_cursor=cursor,
        on_pan_update=on_update, on_pan_end=on_end)


def _layout_note(ui, rec):
    aside = [next((a["name"] for a in ui.apps() if a["id"] == i["app_id"]), "")
             for i in rec["items"] if i.get("minimized")]
    aside = [n for n in aside if n]
    if not aside:
        return ft.Container(height=0)
    names = ", ".join(aside)
    word = "запускается" if len(aside) == 1 else "запускаются"
    return ft.Row([ft.Icon(ft.Icons.LAYERS_CLEAR, size=15, color=C.MUTED_2),
                   T(f"{names} {word} свёрнутым, без места в раскладке", size=11.5,
                     color=C.MUTED, expand=True)],
                  spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)


def _preset_btn(ui, rec, key):
    active = rec["layout"]["preset"] == key
    row = []
    if key != "grid4":
        thumb = ft.Container(width=14, height=11, border_radius=2,
                             border=ft.border.all(1.5, C.TEXT if active else C.MUTED))
        if active and key in ("6040", "half"):
            thumb.border = ft.border.only(
                left=ft.BorderSide(1.5, C.TEXT), top=ft.BorderSide(1.5, C.TEXT),
                bottom=ft.BorderSide(1.5, C.TEXT), right=ft.BorderSide(5, C.TEXT))
        row.append(thumb)
    row.append(T(L.PRESET_LABELS[key], size=12,
                 weight=ft.FontWeight.W_500 if active else ft.FontWeight.W_400,
                 color=C.TEXT if active else C.TEXT_2))
    btn = ft.Container(
        ft.Row(row, spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        height=32, padding=ft.padding.symmetric(0, 11), border_radius=8,
        bgcolor=C.PRESET_ACTIVE_BG if active else None,
        border=ft.border.all(1, C.LINE_5 if active else C.CONTROL),
        on_click=lambda e: ui.set_ops.set_layout_preset(rec["id"], key))
    return btn if active else Wg.hoverable(btn, None, C.SELECTED_BG)


def _order_column(ui, rec):
    head = ft.Row([_caps("ПОРЯДОК ЗАПУСКА"),
                   ft.Container(height=1, bgcolor=C.LINE_2, expand=True)],
                  spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)
    rows = [_order_row(ui, rec, entry) for entry in rec["items"]]
    rows.append(ft.Container(
        ft.Row([ft.Icon(ft.Icons.ADD, size=15, color=C.MUTED_2),
                T("Добавить программу", size=12.5, color=C.MUTED)],
               spacing=7, tight=True, alignment=ft.MainAxisAlignment.CENTER),
        height=44, border_radius=11, border=ft.border.all(1, C.LINE_4),
        alignment=ft.alignment.center,
        on_click=lambda e: ui.context_menus.add_to_set_picker(rec["id"], e)))

    settings = [
        ft.Container(height=1, bgcolor=C.LINE_2, margin=ft.margin.only(top=4)),
        _set_option("Пауза между запусками",
                    ft.Container(T(f"{rec['delay_seconds']:g} с", size=11.5, color=C.TEXT,
                                   font_family="monospace"),
                                 height=30, padding=ft.padding.symmetric(0, 10),
                                 bgcolor=C.PANEL, border=ft.border.all(1, C.CONTROL),
                                 border_radius=8, alignment=ft.alignment.center,
                                 tooltip="Другая пауза",
                                 on_click=lambda e: ui.context_menus.delay_menu(rec, e))),
        _set_option("Закрывать набор целиком",
                    Wg.toggle(rec["close_together"],
                             lambda v: ui.set_ops.set_close_together(rec["id"], v), ui._accent())),
    ]
    return ft.Container(
        ft.Column([head, ft.Column(rows, spacing=6, tight=True)] + settings,
                  spacing=10, tight=True),
        width=C.SET_SIDE_W)


def _set_option(title, control):
    left = [T(title, size=12.5, color=C.TEXT_2)]
    return ft.Row([ft.Column(left, spacing=1, tight=True, expand=True), control],
                  spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)


def _order_row(ui, rec, entry):
    app = next((a for a in ui.apps() if a["id"] == entry["app_id"]), None)
    if app is None:
        return ft.Container(height=0)
    conf = rec["layout"]
    muted = bool(entry.get("minimized")) or entry.get("slot") is None
    place = ("свёрнутым" if entry.get("minimized")
             else L.slot_label(conf["preset"], entry.get("slot"), conf["split"])
             or "без места")
    row = ft.Container(
        ft.Row([
            ft.Icon(ft.Icons.DRAG_INDICATOR, size=16, color=C.TEXT_FAINT),
            ui.icon_slot(app, 30, 9, glyph=16,
                         bgcolor=C.SET_SLOT_BG if muted else None,
                         border=C.SET_SLOT_BORDER if muted else None,
                         glyph_color=C.TEXT_FAINT if muted else None),
            ft.Column([T(app["name"], size=12.5, weight=ft.FontWeight.W_500,
                         color=C.TEXT_2 if muted else C.TEXT, max_lines=1,
                         overflow=ft.TextOverflow.ELLIPSIS),
                       T(place, size=10.5, color=C.MUTED_2, max_lines=1,
                         overflow=ft.TextOverflow.ELLIPSIS)],
                      spacing=1, expand=True, tight=True),
            ft.Container(ft.Icon(ft.Icons.MORE_HORIZ, size=16, color=C.TEXT_FAINT),
                         width=24, height=24, alignment=ft.alignment.center,
                         tooltip="Меню",
                         on_click=lambda e, en=entry: ui.context_menus.set_item_menu(rec, en, e)),
        ], spacing=11, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        height=52, padding=ft.padding.symmetric(0, 12), border_radius=11,
        bgcolor=C.SET_BG if muted else C.PANEL,
        border=ft.border.all(1, C.DASHED if muted else C.LINE))
    Wg.hoverable(row, C.SET_BG if muted else C.PANEL, C.SELECTED_BG)
    tapper = ft.GestureDetector(
        row, on_secondary_tap_down=lambda e, en=entry: ui.context_menus.set_item_menu(rec, en, e))
    group = f"setitem:{rec['id']}"
    rest = C.DASHED if muted else C.LINE
    return ft.DragTarget(
        group=group,
        content=ft.Draggable(group=group, content=tapper, data=entry["app_id"]),
        on_accept=lambda e, r=row: ui.chrome.drop_set_item(rec["id"], entry["app_id"], e, r, rest),
        on_will_accept=lambda e, r=row: ui.chrome.highlight_drop(r, True, rest),
        on_leave=lambda e, r=row: ui.chrome.highlight_drop(r, False, rest))
