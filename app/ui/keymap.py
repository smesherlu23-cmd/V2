from __future__ import annotations

import flet as ft

from ..core import queries
from ..core.hotkeys import is_bindable


class Keymap:
    def __init__(self, ui):
        self.ui = ui

    def handle_key(self, e: ft.KeyboardEvent) -> None:
        key = e.key or ""
        if self.ui.view.capture:
            self._capture_key(e)
            return
        if self.ui.menu.open and key == "Escape":
            self.ui.menu.close()
            return
        if e.ctrl and key.lower() == "k":
            self.ui._focus_search()
            return
        if e.ctrl and key == ",":
            self.ui._open_settings()
            return
        if self.ui.view.palette_open:
            self._palette_key(e, key)
            return
        self._library_key(e, key)

    def _palette_key(self, e, key):
        rows = self.ui._palette_rows()
        actions = queries.palette_actions(self.ui._palette_app())
        count = len(actions) if self.ui.view.palette_focus == "actions" else len(rows)
        if key in ("Arrow Down", "Arrow Up"):
            self.ui.view.move_palette(1 if key == "Arrow Down" else -1, count)
            self.ui._refresh_palette_only()
        elif key == "Tab":
            self.ui.view.focus_palette_actions(len(rows))
            self.ui._refresh_palette_only()
        elif key in ("Enter", "Numpad Enter"):
            self._palette_activate(admin=bool(e.ctrl))
        elif key == "Escape":
            self.ui._close_palette()

    def _palette_activate(self, admin: bool = False):
        if self.ui.view.palette_focus == "actions":
            actions = queries.palette_actions(self.ui._palette_app())
            if actions:
                index = min(self.ui.view.palette_index, len(actions) - 1)
                self.ui.run_palette_action(actions[index]["key"])
            return
        rows = self.ui._palette_rows()
        if not rows:
            return
        row = rows[min(self.ui.view.palette_index, len(rows) - 1)]
        if row["kind"] == "set":
            self.ui.set_ops.launch_set(row["set"]["id"], from_palette=True)
        else:
            self.ui._launch(row["app"]["id"], from_palette=True, as_admin=admin)

    def _library_key(self, e, key):
        if self.ui.view.screen == "triage":
            if self._triage_key(key):
                return
        if key == "Escape":
            if self.ui.view.escape():
                self.ui.refresh()
            else:
                self.ui._hide_to_tray()
        elif e.ctrl and key.lower() == "a" and self.ui.view.screen == "grid":
            self.ui._select_all_visible()
        elif key == "Delete" and self.ui.view.sel:
            self.ui._remove_apps(list(self.ui.view.sel))
        elif e.ctrl and key in ("Enter", "Numpad Enter") and self.ui.view.screen == "add":
            self.ui.scan.commit_add()
        elif key in ("Arrow Right", "Arrow Down"):
            self.ui.move_selection(1)
        elif key in ("Arrow Left", "Arrow Up"):
            self.ui.move_selection(-1)
        elif key in ("Enter", "Numpad Enter"):
            self.ui.activate_selected()

    def _triage_key(self, key) -> bool:
        queue = self.ui.inbox()
        if not queue:
            return False
        item = queue[0]
        picks = queries.suggest_categories(item, self.ui.categories())
        if key in ("1", "2", "3", "4"):
            index = int(key) - 1
            if index < len(picks):
                self.ui.triage.triage_place(item["id"], picks[index]["id"])
            return True
        if key in ("Enter", "Numpad Enter"):
            if picks:
                self.ui.triage.triage_place(item["id"], picks[0]["id"])
            return True
        if key == "Arrow Right":
            self.ui.triage.triage_skip(item["id"])
            return True
        if key == "Delete":
            self.ui.triage.triage_drop(item["id"])
            return True
        return False

    def _capture_key(self, e):
        key = "Space" if e.key == " " else (e.key or "")
        if key in ("Control", "Alt", "Shift", "Meta"):
            return
        if key == "Escape" and not (e.ctrl or e.alt or e.shift or e.meta):
            self.ui._stop_capture()
            self.ui.refresh()
            return
        parts = [name for flag, name in ((e.ctrl, "Ctrl"), (e.alt, "Alt"),
                                         (e.shift, "Shift"), (e.meta, "Win")) if flag]
        accel = "+".join(parts + [key if len(key) > 1 else key.upper()])
        ok, reason = is_bindable(accel)
        if not ok:
            self.ui.toast.error(f"{accel}: {reason}")
            return
        target = self.ui.view.capture_target
        self.ui._stop_capture()
        if target == "launch":
            self.ui._set_launch_hotkey(accel)
        else:
            self.ui._set_hotkey(self.ui.view.inspector, accel)
