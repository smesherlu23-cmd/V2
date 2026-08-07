"""Accelerator parsing and the global-hotkey listener (pynput).

Also assigns the automatic Ctrl+1..9 / Ctrl+Alt+1..9 quick-launch
slots and checks accelerators against Windows' own reserved combos."""

from __future__ import annotations

from ..infra import log

_MODS = {
    "ctrl": "<ctrl>", "control": "<ctrl>",
    "alt": "<alt>", "option": "<alt>",
    "shift": "<shift>",
    "win": "<cmd>", "cmd": "<cmd>", "super": "<cmd>", "meta": "<cmd>",
}

# Flet's KeyboardEvent.key spells several keys differently from pynput —
# "Arrow Up" vs "up", "Escape" vs "esc", "Page Up" vs "page_up". Feeding
# Flet's spelling straight through produced combos like "<arrow up>" that
# pynput's parser refuses, so the binding was dropped at register() time
# while the UI happily showed it as assigned.
_KEY_ALIASES = {
    "arrow up": "up", "arrow down": "down",
    "arrow left": "left", "arrow right": "right",
    "escape": "esc", "return": "enter", "numpad enter": "enter",
    "page up": "page_up", "page down": "page_down",
    "caps lock": "caps_lock", "num lock": "num_lock",
    "scroll lock": "scroll_lock", "print screen": "print_screen",
    "del": "delete", "ins": "insert", "spacebar": "space", " ": "space",
    "break": "pause",
}

# Every pynput Key member worth binding. Anything outside this set (and not
# a single character) cannot become a hotkey, so capture refuses it up
# front instead of letting it silently fail later.
_PYNPUT_KEYS = {
    "backspace", "caps_lock", "delete", "down", "end", "enter", "esc", "home",
    "insert", "left", "menu", "num_lock", "page_down", "page_up", "pause",
    "print_screen", "right", "scroll_lock", "space", "tab", "up",
    "media_next", "media_previous", "media_play_pause",
    "media_volume_up", "media_volume_down", "media_volume_mute",
} | {f"f{n}" for n in range(1, 21)}

# Keys that may be a hotkey all by themselves, because nobody types with
# them. Everything else needs a modifier — see is_bindable.
_STANDALONE_KEYS = {
    "pause", "print_screen", "scroll_lock",
    "media_next", "media_previous", "media_play_pause",
    "media_volume_up", "media_volume_down", "media_volume_mute",
} | {f"f{n}" for n in range(1, 21)}


def canonical_key(token: str) -> str:
    """One spelling for a key, whoever named it (Flet, a data file, a user)."""
    key = str(token or "").strip().lower()
    return _KEY_ALIASES.get(key, key)


def to_pynput(accel: str) -> str:
    out = []
    for raw in str(accel).split("+"):
        p = raw.strip().lower()
        if not p:
            continue
        if p in _MODS:
            out.append(_MODS[p])
            continue
        key = canonical_key(p)
        out.append(key if len(key) == 1 else f"<{key}>")
    return "+".join(out)


_MOD_ORDER = ("ctrl", "alt", "shift", "win")
_MOD_ALIASES = {"control": "ctrl", "option": "alt", "cmd": "win", "super": "win", "meta": "win"}


def split_accel(accel: str) -> tuple[set[str], str]:
    """An accelerator as (modifier names, canonical key)."""
    tokens = [t.strip().lower() for t in str(accel or "").split("+") if t.strip()]
    if not tokens:
        return set(), ""
    mods = {_MOD_ALIASES.get(t, t) for t in tokens[:-1]}
    return mods, canonical_key(tokens[-1])


def normalize_accel(accel: str) -> str:
    mods, key = split_accel(accel)
    if not key:
        return ""
    return "+".join([m for m in _MOD_ORDER if m in mods] + [key])


def is_bindable(accel: str) -> tuple[bool, str]:
    """Whether `accel` can actually become a global hotkey, and why not.

    Checked at capture time so a combination that the listener would drop
    is refused while the user is still looking at the field, rather than
    being stored, displayed as active and never firing.
    """
    mods, key = split_accel(accel)
    if not key:
        return False, "Не разобрал комбинацию"
    if len(key) != 1 and key not in _PYNPUT_KEYS:
        return False, "Эту клавишу назначить нельзя"
    if not mods and key not in _STANDALONE_KEYS:
        # The listener is global, so a bare typing key would be swallowed in
        # every other program too — F-keys and media keys are the ones no
        # one types with, so those alone may stand on their own.
        return False, "Нужен модификатор — Ctrl, Alt, Shift или Win"
    if is_reserved(accel):
        return False, "Комбинацию занимает Windows — система её не отдаст"
    return True, ""

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
            self.bound.add(normalize_accel(accel))
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
        return self.available and normalize_accel(accel) in self.bound

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
        self.available = False
        self.bound = set()


QUICK_SLOTS = 9


def _auto_accels(records, pattern: str, wanted, reserved=()) -> dict[str, str]:
    """Explicit hotkeys, then automatic numbered slots for the rest.

    `reserved` carries combinations already spoken for elsewhere (an app's
    own hotkey when handing out set slots, say). Without it the two
    auto-assigners could both land on Ctrl+Alt+1, and whichever the
    listener saw second was silently dropped.
    """
    accels: dict[str, str] = {}
    used = {normalize_accel(a) for a in reserved if a}
    for rec in records:
        hk = (rec.get("hotkey") or "").strip()
        if hk:
            accels[rec["id"]] = hk
            used.add(normalize_accel(hk))
    slot = 1
    for rec in records:
        if rec["id"] in accels or not wanted(rec):
            continue
        while slot <= QUICK_SLOTS and normalize_accel(pattern.format(slot)) in used:
            slot += 1
        if slot > QUICK_SLOTS:
            break
        accel = pattern.format(slot)
        accels[rec["id"]] = accel
        used.add(normalize_accel(accel))
        slot += 1
    return accels


def quick_accels(apps, reserved=()) -> dict[str, str]:
    return _auto_accels(apps, "Ctrl+{}", lambda a: a.get("quick"), reserved)


def quick_bindings(apps, reserved=()) -> list[tuple[str, str]]:
    return [(accel, app_id) for app_id, accel in quick_accels(apps, reserved).items()]


def free_quick_slot(apps) -> int:
    taken = set()
    for accel in quick_accels(apps).values():
        mods, key = split_accel(accel)
        # Only a plain Ctrl+N occupies a quick slot — Ctrl+Shift+5 used to
        # be read as "slot 5 is taken" because this looked at the last
        # segment alone.
        if mods == {"ctrl"} and key.isdigit():
            taken.add(key)
    return next((n for n in range(1, QUICK_SLOTS + 1) if str(n) not in taken), 0)


def app_for_accel(apps, accel: str) -> str | None:
    want = normalize_accel(accel)
    if not want:
        return None
    return next((aid for aid, ac in quick_accels(apps).items()
                 if normalize_accel(ac) == want), None)


def set_accels(sets, reserved=()) -> dict[str, str]:
    return _auto_accels(sets, "Ctrl+Alt+{}", lambda rec: True, reserved)


def set_bindings(sets, reserved=()) -> list[tuple[str, str]]:
    return [(accel, SET_PREFIX + set_id)
            for set_id, accel in set_accels(sets, reserved).items()]


def set_for_accel(sets, accel: str, reserved=()) -> str | None:
    want = normalize_accel(accel)
    if not want:
        return None
    return next((sid for sid, ac in set_accels(sets, reserved).items()
                 if normalize_accel(ac) == want), None)


def resolve_accels(apps, sets, launch_hotkey: str) -> tuple[dict[str, str], dict[str, str]]:
    """Every accelerator the app hands out, worked out in one pass.

    Priority runs launch hotkey -> apps -> sets, each one seeing what the
    previous took. Callers must use this rather than calling quick_accels
    and set_accels separately, so the rail badges, the tile hints and the
    listener can never disagree about which combination belongs to what.
    """
    app_accels = quick_accels(apps, reserved=[launch_hotkey])
    set_slots = set_accels(sets, reserved=[launch_hotkey, *app_accels.values()])
    return app_accels, set_slots


def split_binding(binding_id: str) -> tuple[str, str]:
    if (binding_id or "").startswith(SET_PREFIX):
        return "set", binding_id[len(SET_PREFIX):]
    return "app", binding_id
