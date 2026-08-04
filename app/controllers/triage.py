from __future__ import annotations

import time


class TriageController:
    def __init__(self, ui):
        self.ui = ui
        self.store = ui.store
        self.notify = ui.notify
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
        self.notify.show(f"{record['name']} → «{cat['name']}»" if cat else record["name"],
                           icon="folder", tone="muted",
                           action=lambda: self._undo_triage(record["id"], item),
                           action_label="Вернуть")
        self.ui.on_library_changed()

    def _undo_triage(self, app_id, item):
        self.done_count = max(0, self.done_count - 1)
        self.store.remove_apps([app_id])
        self.store.restore_inbox(item)
        self.ui.on_library_changed()

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
        self.notify.show(f"{item['name']} не нужен", icon="delete", tone="muted",
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
        self.notify.show(f"Очередь очищена · {len(gone)}", icon="inbox", tone="muted",
                           action=lambda: self._restore_all_inbox(gone), action_label="Вернуть")
        self.ui.refresh()

    def _restore_all_inbox(self, items):
        for item in items:
            self.store.restore_inbox(item)
        self.ui.refresh()
