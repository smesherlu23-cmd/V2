from __future__ import annotations

import time

import flet as ft

from ..ui import colors as C


class TriageController:
    def __init__(self, ui):
        self.ui = ui
        self.store = ui.store
        self.done_count = 0

    def triage_place(self, item_id, cat_id):
        item = self.store.take_inbox(item_id)
        if not item:
            return
        record = self.store.add_app({
            "name": item.get("name"), "path": item.get("path"), "icon": item.get("icon"),
            "icon_fit": item.get("icon_fit"), "sub": item.get("sub", ""),
            "track_exe": item.get("track_exe"), "poster": item.get("poster"),
            "category_id": cat_id})
        self.done_count += 1
        cat = next((c for c in self.ui.categories() if c["id"] == cat_id), None)
        self.ui.toast.show(f"{record['name']} → «{cat['name']}»" if cat else record["name"],
                           icon=ft.Icons.FOLDER, icon_color=C.MUTED,
                           action=lambda: self._undo_triage(record["id"], item),
                           action_label="Вернуть")
        self.ui._on_library_changed()

    def _undo_triage(self, app_id, item):
        self.done_count = max(0, self.done_count - 1)
        self.store.remove_apps([app_id])
        self.store.restore_inbox(item)
        self.ui._on_library_changed()

    def triage_skip(self, item_id):
        item = self.store.take_inbox(item_id)
        if not item:
            return
        item["order"] = int(time.time() * 1000)
        self.store.restore_inbox(item)
        self.ui.refresh()

    def triage_drop(self, item_id):
        item = self.store.take_inbox(item_id)
        if not item:
            return
        self.ui.toast.show(f"{item['name']} не нужен", icon=ft.Icons.DELETE_OUTLINE,
                           icon_color=C.MUTED,
                           action=lambda: self._restore_inbox(item), action_label="Вернуть")
        self.ui.refresh()

    def _restore_inbox(self, item):
        self.store.restore_inbox(item)
        self.ui.refresh()

    def triage_defer_all(self):
        gone = self.store.clear_inbox()
        if not gone:
            return
        self.ui.view.set_screen("grid")
        self.ui.toast.show(f"Очередь очищена · {len(gone)}", icon=ft.Icons.INBOX,
                           icon_color=C.MUTED,
                           action=lambda: self._restore_all_inbox(gone), action_label="Вернуть")
        self.ui.refresh()

    def _restore_all_inbox(self, items):
        for item in items:
            self.store.restore_inbox(item)
        self.ui.refresh()
