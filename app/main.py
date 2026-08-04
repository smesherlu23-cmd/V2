from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path

import flet as ft

from app.core.hotkeys import (TOGGLE_LAUNCH, HotkeyManager, app_for_accel, quick_bindings,
                              set_bindings, set_for_accel, split_binding)
from app.core.store import DEFAULT_LAUNCH_HOTKEY, Store
from app.infra import log
from app.infra.debounce import Debounce
from app.platform import autostart
from app.platform.launcher import Launcher
from app.platform.tray import TrayController
from app.ui import colors as C
from app.ui.app import CenturioUI
from app.ui.iconify import ensure_icons

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
GEOMETRY_FLUSH_DELAY = 0.5
AUTO_RESCAN_INTERVAL = 900


def shutdown(store=None, tray=None, launcher=None, hotkeys=None, geometry_flush=None,
             toast=None):
    for label, step in (("flushing the store", getattr(store, "flush", None)),
                        ("cancelling the geometry flush",
                         getattr(geometry_flush, "cancel", None)),
                        ("stopping the toast timer", getattr(toast, "stop", None)),
                        ("stopping the hotkey listener", getattr(hotkeys, "stop", None)),
                        ("stopping the process monitor",
                         getattr(launcher, "stop_monitor", None)),
                        ("stopping the tray icon", getattr(tray, "stop", None))):
        if step is None:
            continue
        try:
            step()
        except Exception:
            log.exception("%s on quit failed", label)


def main(page: ft.Page):
    store = Store()
    log.setup(log_dir=Path(store.path).parent,
              debug=log.is_debug() or bool(store.state()["settings"].get("debug_log")))
    log.debug("Centurio starting (argv=%s)", sys.argv)

    icon_path = ensure_icons(ASSETS_DIR)
    is_web = page.web or os.environ.get("CENTURIO_WEB") == "1"
    start_hidden = "--hidden" in sys.argv

    page.title = "Centurio"
    page.bgcolor = C.BG_1
    page.padding = 0
    page.spacing = 0
    page.theme_mode = ft.ThemeMode.DARK
    page.fonts = {
        "Inter": "fonts/Inter-Regular.ttf",
        "Inter SemiBold": "fonts/Inter-SemiBold.ttf",
        "Inter Bold": "fonts/Inter-Bold.ttf",
        "Inter ExtraBold": "fonts/Inter-ExtraBold.ttf",
        "mono": "fonts/Mono-Regular.ttf",
    }
    page.theme = ft.Theme(color_scheme_seed=C.ACCENT, font_family="Inter")

    if not is_web:
        page.window.title_bar_hidden = True
        page.window.frameless = True
        page.window.prevent_close = True

    launcher = Launcher()
    hotkeys = None
    geometry_flush = None
    ui_holder = {}

    def quit_app():
        ui = ui_holder.get("ui")
        shutdown(store=store, tray=tray, launcher=launcher, hotkeys=hotkeys,
                 geometry_flush=geometry_flush, toast=getattr(ui, "toast", None))
        _quit(page)

    def apply_window():
        if is_web:
            return
        try:
            s = store.state()["settings"]
            page.window.resizable = True
            page.window.min_width = C.LIBRARY_MIN_W
            page.window.min_height = C.LIBRARY_MIN_H
            page.window.width = s.get("win_w") or C.LIBRARY_W
            page.window.height = s.get("win_h") or C.LIBRARY_H
            if s.get("win_x") is not None and s.get("win_y") is not None:
                page.window.left = s["win_x"]
                page.window.top = s["win_y"]
            else:
                page.window.center()
            if s.get("win_max"):
                page.window.maximized = True
            page.update()
        except Exception:
            log.exception("восстановление геометрии окна ошибка")

    def open_search():
        ui = ui_holder.get("ui")
        _show_window(page)
        if ui is not None:
            ui._focus_search()

    def open_library():
        ui = ui_holder.get("ui")
        _show_window(page)
        if ui is not None:
            ui.open_library()

    def toggle_launch():
        ui = ui_holder.get("ui")
        if ui is None:
            return
        visible = True if is_web else bool(page.window.visible)
        if visible:
            hide_to_tray()
        else:
            open_library()

    def minimize():
        if store.state()["settings"].get("minimize_to_tray") and tray.available:
            hide_to_tray()
        else:
            page.window.minimized = True
            page.update()

    def toggle_maximize():
        page.window.maximized = not page.window.maximized
        page.update()

    def close():
        if store.state()["settings"].get("close_to_tray") and tray.available:
            hide_to_tray()
        else:
            quit_app()

    def hide_to_tray():
        if is_web:
            return
        if tray.available:
            _hide_window(page)
        else:
            page.window.minimized = True
            page.update()

    def on_setting(key, value):
        if key == "autostart":
            autostart.set_autostart(bool(value))
        elif key == "launch_hotkey":
            refresh_runtime()

    def on_hotkey(binding_id):
        if binding_id == TOGGLE_LAUNCH:
            toggle_launch()
            return
        ui = ui_holder.get("ui")
        if ui is None:
            return
        kind, target = split_binding(binding_id)
        if kind == "set":
            ui._launch_set(target)
        else:
            ui._launch(target)

    hotkeys = HotkeyManager(on_trigger=on_hotkey)

    def refresh_runtime():
        state = store.state()
        launcher.set_apps(state["apps"])
        tray.refresh()
        if not is_web:
            bindings = [(state["settings"].get("launch_hotkey") or DEFAULT_LAUNCH_HOTKEY,
                         TOGGLE_LAUNCH)]
            bindings += quick_bindings(state["apps"])
            bindings += set_bindings(_ordered_sets(state))
            hotkeys.register(bindings)

    controllers = {
        "minimize": minimize, "toggle_maximize": toggle_maximize, "close": close,
        "hide_to_tray": hide_to_tray, "on_setting": on_setting,
        "on_library_changed": refresh_runtime,
        "suspend_hotkeys": hotkeys.stop, "resume_hotkeys": refresh_runtime,
    }

    def tray_menu():
        from app import dialogs
        items = [(item["label"], (lambda aid=item["id"]: on_hotkey(aid)))
                 for item in dialogs.tray_items(store)]
        return items, dialogs.library_summary(store)

    tray = TrayController(icon_path, on_show=open_search, on_quit=quit_app,
                          on_open_library=open_library, menu_provider=tray_menu)

    ui = CenturioUI(page, store, launcher, controllers)
    ui_holder["ui"] = ui
    launcher.on_change = lambda ids: ui.set_running(ids)

    def on_key(e: ft.KeyboardEvent):
        try:
            ui.handle_key(e)
        except Exception:
            log.exception("управление нажатием клавиши ошибка")
        if e.ctrl and (e.key or "").isdigit():
            accel = f"Ctrl+Alt+{e.key}" if e.alt else f"Ctrl+{e.key}"
            if hotkeys.handles(accel):
                return
            state = store.state()
            if e.alt:
                set_id = set_for_accel(_ordered_sets(state), accel)
                if set_id:
                    ui._launch_set(set_id)
                return
            app_id = app_for_accel(state["apps"], accel)
            if app_id:
                ui._launch(app_id)
    page.on_keyboard_event = on_key

    def _flush_geometry():
        try:
            store.flush()
        except Exception:
            log.exception("сбой в геометрии окна промывки")
        try:
            ui.refresh()
        except Exception:
            log.exception("сбой при перерисовке после изменения размера")

    geometry_flush = Debounce(GEOMETRY_FLUSH_DELAY, _flush_geometry)

    def save_window(flush: bool = False):
        try:
            w, h = page.window.width, page.window.height
            maximized = page.window.maximized
            store.set_setting("win_max", maximized, persist=False)
            if not maximized:
                if w and h:
                    store.set_setting("win_w", int(w), persist=False)
                    store.set_setting("win_h", int(h), persist=False)
                if page.window.left is not None and page.window.top is not None:
                    store.set_setting("win_x", int(page.window.left), persist=False)
                    store.set_setting("win_y", int(page.window.top), persist=False)
        except Exception:
            log.exception("сбой при сохранении геометрии окна")
            return
        geometry_flush.schedule(immediate=flush)

    def on_win_event(e):
        if e.data in ("resized", "moved", "maximize", "unmaximize"):
            save_window()
        elif e.data == "close":
            save_window(flush=True)
            close()
    page.window.on_event = on_win_event if not is_web else None

    apply_window()
    ui.mount()

    def _backfill():
        try:
            from app import discovery
            cache = str(app_paths_dir(store))
            schema = store.state()["settings"].get("icon_schema", 0)
            refresh = schema < discovery.ICON_SCHEMA
            if discovery.backfill_icons(store, cache, refresh=refresh):
                ui.refresh()
            if refresh:
                store.set_setting("icon_schema", discovery.ICON_SCHEMA)
        except Exception:
            log.exception("сбой при заполнении значков")
    threading.Thread(target=_backfill, daemon=True).start()
    refresh_runtime()
    launcher.start_monitor()

    def _auto_rescan_loop():
        while True:
            time.sleep(AUTO_RESCAN_INTERVAL)
            try:
                if store.state()["settings"].get("auto_rescan"):
                    ui.rescan(silent=True)
            except Exception:
                log.exception("ошибка автоматической повторной проверки галочки")
    threading.Thread(target=_auto_rescan_loop, daemon=True).start()

    if not is_web:
        want = bool(store.state()["settings"].get("autostart", False))
        effective = autostart.sync(want)
        if effective != want:
            store.set_setting("autostart", effective)
            ui.refresh()
        tray.start()
        if start_hidden:
            _hide_window(page)
    ui.maybe_onboard()


def _ordered_sets(state) -> list[dict]:
    return sorted(state["sets"], key=lambda s: s.get("order", 0))


def app_paths_dir(store):
    return Path(store.path).parent / "icons"


def _show_window(page):
    try:
        page.window.visible = True
        page.window.minimized = False
        page.update()
    except Exception:
        log.exception("не удалось восстановить окно")
    try:
        page.window.to_front()
        page.window.focused = True
        page.update()
    except Exception:
        log.exception("не удалось переместить окно на передний план")


def _hide_window(page):
    try:
        page.window.visible = False
        page.update()
    except Exception:
        log.exception("не удалось скрыть окно")


def _quit(page):
    try:
        page.window.prevent_close = False
        page.window.destroy()
    except Exception:
        log.exception("не удалось закрыть окно, выход вручную")
        os._exit(0)