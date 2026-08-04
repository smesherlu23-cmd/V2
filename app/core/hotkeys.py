from __future__ import annotations

from ..infra import log

_MODS = {
    "ctrl": "<ctrl>", "control": "<ctrl>",
    "alt": "<alt>", "option": "<alt>",
    "shift": "<shift>",
    "win": "<cmd>", "cmd": "<cmd>", "super": "<cmd>", "meta": "<cmd>",
}


def to_pynput(accel: str) -> str:
    out = []
    for raw in str(accel).split("+"):
        p = raw.strip().lower()
        if not p:
            continue
        if p in _MODS:
            out.append(_MODS[p])
        elif len(p) == 1:
            out.append(p)
        else:
            out.append(f"<{p}>")
    return "+".join(out)


_MOD_ORDER = ("ctrl", "alt", "shift", "win")
_MOD_ALIASES = {"control": "ctrl", "option": "alt", "cmd": "win", "super": "win", "meta": "win"}


def normalize_accel(accel: str) -> str:
    tokens = [t.strip().lower() for t in str(accel or "").split("+") if t.strip()]
    if not tokens:
        return ""
    key = tokens[-1]
    mods = {_MOD_ALIASES.get(t, t) for t in tokens[:-1]}
    return "+".join([m for m in _MOD_ORDER if m in mods] + [key])

RESERVED_COMBOS = {normalize_accel(c) for c in (
    "Alt+F4", "Alt+Tab", "Alt+Shift+Tab", "Ctrl+Alt+Tab", "Alt+Esc", "Alt+Escape",
    "Ctrl+Esc", "Ctrl+Shift+Esc", "Ctrl+Alt+Delete", "Ctrl+Alt+Del",
    "Win+L", "Win+D", "Win+E", "Win+R", "Win+I", "Win+A", "Win+X", "Win+U",
    "Win+P", "Win+S", "Win+Q", "Win+M", "Win+Tab", "Win+Pause", "Win+Comma",
    "Win+Period", "Win+Space", "Win+Shift+S", "Win+Ctrl+D", "Win+Ctrl+F4",
    "Win+Ctrl+Left", "Win+Ctrl+Right", "Win+Shift+M", "Win+Break",
)}


def is_reserved(accel: str) -> bool:
    return normalize_accel(accel) in RESERVED_COMBOS


_KEY_LABELS = {"space": "Пробел", "enter": "Ввод", "esc": "Esc", "escape": "Esc",
               "tab": "Tab", "backspace": "Backspace"}


def format_accel(accel: str | None) -> str:
    if not accel:
        return "не задана"
    parts = []
    for raw in str(accel).split("+"):
        token = raw.strip()
        if not token:
            continue
        parts.append(_KEY_LABELS.get(token.lower(), token if len(token) > 1 else token.upper()))
    return "+".join(parts)


TOGGLE_LAUNCH = "__centurio_toggle_launch__"
SET_PREFIX = "set:"


class HotkeyManager:
    def __init__(self, on_trigger):
        self.on_trigger = on_trigger
        self._listener = None
        self.available = False
        self.rejected: list[str] = []
        self.bound: set[str] = set()

    def _build_mapping(self, keyboard, bindings):
        parse = getattr(keyboard.HotKey, "parse", None)
        mapping = {}
        rejected = []
        self.bound = set()
        for accel, app_id in bindings:
            if not accel:
                continue
            combo = to_pynput(accel)
            if not combo:
                continue
            if parse is not None:
                try:
                    parse(combo)
                except Exception:
                    rejected.append(accel)
                    log.warning("ignoring unparseable hotkey %r (as %r)", accel, combo)
                    continue
            if combo in mapping:
                rejected.append(accel)
                log.warning("ignoring duplicate hotkey %r", accel)
                continue
            mapping[combo] = (lambda aid=app_id: self._fire(aid))
            self.bound.add(accel.strip().lower())
        return mapping, rejected

    def register(self, bindings) -> bool:
        self.stop()
        self.rejected = []
        self.bound = set()
        try:
            from pynput import keyboard
        except Exception:
            self.available = False
            return False

        mapping, self.rejected = self._build_mapping(keyboard, bindings)
        if not mapping:
            self.available = False
            self.bound = set()
            return False
        try:
            self._listener = keyboard.GlobalHotKeys(mapping)
            self._listener.daemon = True
            self._listener.start()
            self.available = True
            return True
        except Exception:
            log.exception("failed to start the global hotkey listener")
            self.available = False
            self.bound = set()
            return False

    def handles(self, accel: str) -> bool:
        return self.available and (accel or "").strip().lower() in self.bound

    def _fire(self, app_id):
        try:
            self.on_trigger(app_id)
        except Exception:
            log.exception("global hotkey handler for %s failed", app_id)

    def stop(self):
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None


QUICK_SLOTS = 9


def quick_accels(apps) -> dict[str, str]:
    accels: dict[str, str] = {}
    used: set[str] = set()
    for a in apps:
        hk = (a.get("hotkey") or "").strip()
        if hk:
            accels[a["id"]] = hk
            used.add(hk.lower())
    slot = 1
    for a in apps:
        if not a.get("quick") or a["id"] in accels:
            continue
        while slot <= QUICK_SLOTS and f"ctrl+{slot}" in used:
            slot += 1
        if slot > QUICK_SLOTS:
            break
        accel = f"Ctrl+{slot}"
        accels[a["id"]] = accel
        used.add(accel.lower())
        slot += 1
    return accels


def quick_bindings(apps) -> list[tuple[str, str]]:
    return [(accel, app_id) for app_id, accel in quick_accels(apps).items()]


def free_quick_slot(apps) -> int:
    taken = {a.split("+")[-1] for a in quick_accels(apps).values()}
    return next((n for n in range(1, QUICK_SLOTS + 1) if str(n) not in taken), 0)


def app_for_accel(apps, accel: str) -> str | None:
    want = (accel or "").strip().lower()
    if not want:
        return None
    return next((aid for aid, ac in quick_accels(apps).items() if ac.lower() == want), None)


def set_accels(sets) -> dict[str, str]:
    accels: dict[str, str] = {}
    used: set[str] = set()
    for rec in sets:
        hk = (rec.get("hotkey") or "").strip()
        if hk:
            accels[rec["id"]] = hk
            used.add(hk.lower())
    slot = 1
    for rec in sets:
        if rec["id"] in accels:
            continue
        while slot <= QUICK_SLOTS and f"ctrl+alt+{slot}" in used:
            slot += 1
        if slot > QUICK_SLOTS:
            break
        accel = f"Ctrl+Alt+{slot}"
        accels[rec["id"]] = accel
        used.add(accel.lower())
        slot += 1
    return accels


def set_bindings(sets) -> list[tuple[str, str]]:
    return [(accel, SET_PREFIX + set_id) for set_id, accel in set_accels(sets).items()]


def set_for_accel(sets, accel: str) -> str | None:
    want = (accel or "").strip().lower()
    if not want:
        return None
    return next((sid for sid, ac in set_accels(sets).items() if ac.lower() == want), None)


def split_binding(binding_id: str) -> tuple[str, str]:
    if (binding_id or "").startswith(SET_PREFIX):
        return "set", binding_id[len(SET_PREFIX):]
    return "app", binding_id
