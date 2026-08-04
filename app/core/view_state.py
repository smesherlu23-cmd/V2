from __future__ import annotations

from . import queries

MODE_KEYS = ("grid", "list")
SCREENS = ("grid", "add", "settings", "triage")
PALETTE_FOCUS = ("results", "actions")


class ViewState:

    def __init__(self, store):
        self.store = store
        state = store.state()
        s = state["settings"]
        self.filter = queries.valid_filter(s.get("view_filter") or "all",
                                           state["categories"])
        self.query = ""
        self.sort = s.get("view_sort") if s.get("view_sort") in queries.SORT_KEYS else "alpha"
        self.mode = s.get("view_mode") if s.get("view_mode") in MODE_KEYS else "grid"
        self.sidebar_open = True
        self.selected = -1
        self.screen = "grid"
        self.palette_open = False
        self.palette_index = 0
        self.palette_focus = "results"
        self.inspector: str | None = None
        self.sel: list[str] = []
        self.adv = False
        self.capture = False
        self.capture_target = "app"

        self.select_mode = False
        self.selection_anchor: str | None = None

        self.active_set: str | None = None
        collapsed = s.get("collapsed")
        self.collapsed: set[str] = {c for c in collapsed if isinstance(c, str)} \
            if isinstance(collapsed, list) else set()

        self.settings_tab = "view"

        self.popover: str | None = None

        self.only_new = True
        self.add_query = ""
        self.manual_path = ""
        self.add_sel: set[str] = set()
        self.add_cat: dict[str, str] = {}

        self.onboarding = False

    def is_all_view(self):
        return self.filter == "all"

    def persist(self):
        self.store.set_setting("view_filter", self.filter, persist=False)
        self.store.set_setting("view_sort", self.sort, persist=False)
        self.store.set_setting("view_mode", self.mode)

    def set_filter(self, f):
        self.filter = f
        self.selected = -1
        self.screen = "grid"
        self.active_set = None
        self.close_inspector()
        self.persist()

    def set_query(self, q):
        self.query = q
        self.palette_index = 0
        self.palette_focus = "results"

    def set_mode(self, m):
        self.mode = m
        self.persist()

    def set_sort(self, s):
        if s in queries.SORT_KEYS:
            self.sort = s
            self.persist()

    def cycle_sort(self):
        cur = self.sort if self.sort in queries.SORT_KEYS else "alpha"
        self.set_sort(queries.SORT_KEYS[(queries.SORT_KEYS.index(cur) + 1) % len(queries.SORT_KEYS)])

    def toggle_sidebar(self):
        self.sidebar_open = not self.sidebar_open

    def revalidate(self, categories):
        new = queries.valid_filter(self.filter, categories)
        if new != self.filter:
            self.filter = new
            self.persist()
        if self.popover and not any(c["id"] == self.popover for c in categories):
            self.close_popover()

    def move_selection(self, delta, count):
        if not count:
            self.selected = -1
            return
        cur = self.selected if self.selected >= 0 else (-1 if delta > 0 else 0)
        self.selected = max(0, min(count - 1, cur + delta))

    def set_screen(self, screen: str):
        if screen in SCREENS:
            self.screen = screen
            self.active_set = None
            self.close_palette()
            self.close_inspector()

    def open_set(self, set_id: str):
        self.active_set = set_id
        self.screen = "grid"
        self.close_palette()
        self.close_inspector()

    def close_set(self):
        self.active_set = None

    def open_palette(self):
        self.palette_open = True
        self.palette_index = 0
        self.palette_focus = "results"

    def close_palette(self):
        self.palette_open = False
        self.query = ""
        self.palette_index = 0
        self.palette_focus = "results"

    def move_palette(self, delta: int, count: int):
        if count <= 0:
            self.palette_index = 0
            return
        self.palette_index = max(0, min(count - 1, self.palette_index + delta))

    def focus_palette_actions(self, count: int):
        if self.palette_focus == "results" and count:
            self.palette_focus = "actions"
            self.palette_index = 0
        else:
            self.palette_focus = "results"
            self.palette_index = 0

    def clear_selection(self):
        self.sel = []
        self.selection_anchor = None

    def select_one(self, app_id: str):
        self.sel = [app_id]
        self.inspector = app_id
        self.selection_anchor = app_id

    def toggle_selection(self, app_id: str):
        if app_id in self.sel:
            self.sel = [i for i in self.sel if i != app_id]
        else:
            self.sel = self.sel + [app_id]
        self.selection_anchor = app_id
        if not self.select_mode:
            self.inspector = self.sel[-1] if self.sel else None

    def select_many(self, app_ids):
        for app_id in app_ids:
            if app_id not in self.sel:
                self.sel.append(app_id)
        if self.sel and not self.select_mode:
            self.inspector = self.sel[-1]

    def select_range(self, app_ids, app_id):
        ids = list(app_ids)
        if app_id not in ids:
            return
        anchor = self.selection_anchor if self.selection_anchor in ids else app_id
        lo, hi = sorted((ids.index(anchor), ids.index(app_id)))
        self.select_many(ids[lo:hi + 1])

    def enter_select_mode(self):
        self.select_mode = True
        self.inspector = None
        self.capture = False
        self.close_palette()

    def leave_select_mode(self):
        self.select_mode = False
        self.clear_selection()

    def drop_missing(self, live_ids):
        live = set(live_ids)
        self.sel = [i for i in self.sel if i in live]
        if self.selection_anchor not in live:
            self.selection_anchor = None
        if self.inspector not in live:
            self.inspector = None
            if self.capture_target == "app":
                self.capture = False

    def close_inspector(self):
        self.inspector = None
        self.capture = False
        self.clear_selection()

    def toggle_section(self, cid: str):
        if cid in self.collapsed:
            self.collapsed.discard(cid)
        else:
            self.collapsed.add(cid)
        self.store.set_setting("collapsed", sorted(self.collapsed), persist="debounce")

    def open_popover(self, cat_id: str):
        self.popover = cat_id

    def close_popover(self):
        self.popover = None

    def reset_add(self):
        self.add_sel = set()
        self.add_cat = {}
        self.add_query = ""
        self.manual_path = ""

    def toggle_add(self, key: str):
        if key in self.add_sel:
            self.add_sel.discard(key)
        else:
            self.add_sel.add(key)

    def set_add_group(self, keys, checked: bool):
        for key in keys:
            if checked:
                self.add_sel.add(key)
            else:
                self.add_sel.discard(key)

    def escape(self) -> bool:
        if self.popover:
            self.close_popover()
            return True
        if self.capture:
            self.capture = False
            return True
        if self.palette_open:
            self.close_palette()
            return True
        if self.select_mode:
            self.leave_select_mode()
            return True
        if self.screen != "grid":
            self.set_screen("grid")
            return True
        if self.active_set:
            self.close_set()
            return True
        if self.inspector or self.sel:
            self.close_inspector()
            return True
        if self.selected >= 0:
            self.selected = -1
            return True
        return False
