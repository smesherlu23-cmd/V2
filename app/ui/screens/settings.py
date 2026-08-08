from __future__ import annotations

import flet as ft

from ... import __version__
from ...core.hotkeys import format_accel
from .. import colors as C
from .. import widgets as Wg
from ..format import T
from .common import _caps, _screen_header

ACCENT_NAMES = dict(zip(C.ACCENT_CHOICES, ("Белый", "Синий", "Бирюзовый", "Оранжевый")))


SETTINGS_TABS = (
    ("view", "Вид", ft.Icons.PALETTE),
    ("keys", "Клавиши", ft.Icons.KEYBOARD),
    ("startup", "Запуск и трей", ft.Icons.POWER_SETTINGS_NEW),
    ("library", "Библиотека", ft.Icons.STORAGE),
)


def build_settings_screen(ui):
    tab = ui.view.settings_tab
    nav_rows = [_settings_nav_row(ui, key, label, icon, key == tab)
                for key, label, icon in SETTINGS_TABS]
    nav = ft.Container(
        ft.Column(nav_rows + [ft.Container(expand=True),
                              T(f"Centurio v{__version__}", size=11, color=C.MUTED_3,
                                font_family="monospace")],
                  spacing=3, expand=True),
        width=C.SETTINGS_NAV_W, padding=ft.padding.only(14, 18, 14, 20),
        border=ft.border.only(right=ft.BorderSide(1, C.LINE_2)))

    body = ft.Container(
        ft.Column(_settings_pane(ui, tab), spacing=17, scroll=ft.ScrollMode.AUTO,
                  expand=True),
        expand=True, padding=ft.padding.only(28, 20, 28, 24))

    return ft.Column([
        _screen_header("Настройки", "Всё сохраняется само", ui.back_to_grid),
        ft.Row([nav, body], spacing=0, expand=True,
               vertical_alignment=ft.CrossAxisAlignment.START),
    ], spacing=0, expand=True)


def _settings_nav_row(ui, key, label, icon, active):
    row = ft.Container(
        ft.Row([ft.Icon(icon, size=16, color=C.TEXT if active else C.MUTED_2),
                T(label, size=13, color=C.TEXT if active else C.MUTED,
                  weight=ft.FontWeight.W_600 if active else ft.FontWeight.W_400)],
               spacing=11, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        height=38, border_radius=9, padding=ft.padding.symmetric(0, 11),
        on_click=lambda e: ui.set_settings_tab(key))
    if active:
        row.bgcolor = C.PANEL_ACTIVE
        return row
    return Wg.hoverable(row, None, C.SELECTED_BG)


def _group(label, control):
    return ft.Column([_caps(label), ft.Row([control], tight=True)],
                     spacing=9, tight=True)


def _settings_pane(ui, tab):
    if tab == "keys":
        return _settings_keys(ui)
    if tab == "startup":
        return _settings_startup(ui)
    if tab == "library":
        return _settings_library(ui)
    return _settings_view(ui)


def _settings_view(ui):
    swatches = ft.Row([
        ft.Container(width=30, height=30, border_radius=9, bgcolor=col,
                     border=ft.border.all(2, C.ACCENT) if col == ui._accent()
                     else ft.border.all(1, C.LINE_4),
                     tooltip=ACCENT_NAMES.get(col),
                     on_click=lambda e, c=col: ui.set_setting("accent", c))
        for col in C.ACCENT_CHOICES], spacing=9, tight=True)
    return [
        _group("АКЦЕНТ", swatches),
        _group("ПЛОТНОСТЬ", _tile_segments(ui)),
        _group("ПОЛОСА КАТЕГОРИЙ", _rail_segments(ui)),
        ft.Container(height=1, bgcolor=C.LINE_2),
        _switch(ui, "Показывать «Быстрый запуск»", "show_quick_row"),
        _switch(ui, "Постеры для игр", "game_posters"),
    ]


def _launch_hotkey_field(ui):
    capturing = ui.view.capture and ui.view.capture_target == "launch"
    explicit = ui.setting("launch_hotkey")
    label = "нажмите…" if capturing else format_accel(explicit)
    return ft.Container(
        ft.Row([T(label, size=11.5, color=C.TEXT, font_family="monospace"),
                ft.Icon(ft.Icons.EDIT, size=14, color=C.MUTED_2)],
               spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        height=32, padding=ft.padding.symmetric(0, 12), bgcolor=C.PANEL,
        border=ft.border.all(1, ui._accent() if capturing else C.TOAST_BORDER),
        border_radius=8, alignment=ft.alignment.center,
        tooltip="Нажмите комбинацию" if capturing else "Другая комбинация",
        on_click=lambda e: ui._begin_capture("launch"))


def _settings_keys(ui):
    return [
        _row("Вызов Centurio", _launch_hotkey_field(ui)),
        ft.Container(height=1, bgcolor=C.LINE_2),
        _settings_note("Своя комбинация для отдельной программы задаётся в панели "
                       "справа от неё, а Ctrl+1…9 раздаются закреплённым в "
                       "«Быстром запуске» сами. Комбинации, которые уже что-то "
                       "делают в Windows — Alt+F4, Win+L и подобные — назначить нельзя."),
    ]


def _settings_startup(ui):
    return [
        _switch(ui, "Запускать с Windows", "autostart"),
        _switch(ui, "Крестик сворачивает в трей", "close_to_tray"),
        _switch(ui, "Прятать окно после запуска", "hide_after"),
    ]


def _settings_library(ui):
    size = ui.icon_cache_size()
    cache_label = f"{size / (1024 * 1024):.0f} МБ" if size else "пусто"
    return [
        _switch(ui, "Складывать новое в разбор", "triage"),
        _switch(ui, "Проверять новое раз в 15 минут", "auto_rescan"),
        ft.Container(height=1, bgcolor=C.LINE_2),
        _row("Кэш иконок",
             ft.Row([T(cache_label, size=11, color=C.MUTED_2, font_family="monospace"),
                     Wg.link_btn("Очистить", ui.clear_icon_cache)], spacing=10, tight=True)),
        _row("Копия библиотеки",
             Wg.outline_btn("Сохранить", ui.backup, ft.Icons.BACKUP, height=32)),
        _row("Файл библиотеки", Wg.link_btn("Показать в папке", ui.show_data_folder)),
        ft.Container(height=1, bgcolor=C.LINE_2),
        _switch(ui, "Подробный лог", "debug_log"),
    ]


def _settings_note(text):
    return ft.Container(
        T(text, size=11.5, color=C.TEXT_DIM),
        padding=ft.padding.all(12), border_radius=10, bgcolor=C.PANEL,
        border=ft.border.all(1, C.LINE_2))


def _row(title, control, on_click=None):
    return ft.Container(
        ft.Row([T(title, size=13, color=C.TEXT_2, expand=True), control],
               spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        on_click=(lambda e: on_click()) if on_click else None)


def _switch(ui, title, key):
    value = bool(ui.setting(key))
    return _row(title,
                Wg.toggle(value, lambda v, k=key: ui.set_setting(k, v), ui._accent()),
                on_click=lambda k=key, v=value: ui.set_setting(k, not v))


def _segments(ui, key, default, options):
    def segment(label, value):
        active = ui.setting(key, default) == value
        return ft.Container(
            T(label, size=12, weight=ft.FontWeight.W_600 if active else ft.FontWeight.W_400,
              color=C.TEXT if active else C.MUTED),
            height=26, padding=ft.padding.symmetric(0, 12), border_radius=6,
            bgcolor=C.PANEL_ACTIVE if active else None, alignment=ft.alignment.center,
            on_click=lambda e, v=value: ui.set_setting(key, v))
    return ft.Container(ft.Row([segment(label, value) for label, value in options], spacing=0),
                        bgcolor=C.PANEL, border=ft.border.all(1, C.SEGMENT_BORDER),
                        border_radius=8, padding=ft.padding.all(2))


def _tile_segments(ui):
    return _segments(ui, "tile_size", "large",
                     (("Крупные", "large"), ("Плотные", "compact")))


def _rail_segments(ui):
    return _segments(ui, "rail_size", C.DEFAULT_RAIL_SIZE,
                     (("Обычная", "normal"), ("Крупная", "large"), ("Огромная", "huge")))
