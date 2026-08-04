from __future__ import annotations

PRESETS = ("full", "6040", "half", "grid4")

PRESET_LABELS = {"full": "На весь экран", "6040": "60 / 40", "half": "Пополам",
                 "grid4": "Сетка 2×2"}

SPLIT_PRESETS = ("6040", "half", "grid4")

DEFAULT_PRESET = "6040"
DEFAULT_SPLIT = 0.6
DEFAULT_VSPLIT = 0.5
MIN_SPLIT = 0.2
MAX_SPLIT = 0.8


def clamp(value, low=0.0, high=1.0) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return low
    return max(low, min(high, value))


def valid_preset(name) -> str:
    return name if name in PRESETS else DEFAULT_PRESET


def slots(preset: str, split: float = DEFAULT_SPLIT,
          vsplit: float = DEFAULT_VSPLIT) -> list[tuple[float, float, float, float]]:
    preset = valid_preset(preset)
    s = clamp(split, MIN_SPLIT, MAX_SPLIT)
    v = clamp(vsplit, MIN_SPLIT, MAX_SPLIT)
    if preset == "full":
        return [(0.0, 0.0, 1.0, 1.0)]
    if preset == "half":
        return [(0.0, 0.0, s, 1.0), (s, 0.0, 1.0 - s, 1.0)]
    if preset == "grid4":
        return [(0.0, 0.0, s, v), (s, 0.0, 1.0 - s, v),
                (0.0, v, s, 1.0 - v), (s, v, 1.0 - s, 1.0 - v)]
    return [(0.0, 0.0, s, 1.0), (s, 0.0, 1.0 - s, v), (s, v, 1.0 - s, 1.0 - v)]


def slot_count(preset: str) -> int:
    return len(slots(preset))


def slot_label(preset: str, index: int, split: float = DEFAULT_SPLIT) -> str:
    preset = valid_preset(preset)
    if index is None or not 0 <= index < slot_count(preset):
        return ""
    if preset == "full":
        return "на весь экран"
    percent = round(clamp(split, MIN_SPLIT, MAX_SPLIT) * 100)
    if preset == "half":
        return f"слева · {percent}%" if index == 0 else f"справа · {100 - percent}%"
    if preset == "grid4":
        return ("слева сверху", "справа сверху", "слева снизу", "справа снизу")[index]
    return (f"слева · {percent}%", "справа сверху", "справа снизу")[index]


def rect_for(item: dict, preset: str, split: float = DEFAULT_SPLIT,
             vsplit: float = DEFAULT_VSPLIT):
    if item.get("minimized"):
        return None
    rect = normal_rect(item.get("rect"))
    if rect is not None:
        return rect
    index = item.get("slot")
    if not isinstance(index, int):
        return None
    places = slots(preset, split, vsplit)
    return places[index] if 0 <= index < len(places) else None


def normal_rect(value):
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    try:
        x, y, w, h = (float(v) for v in value)
    except (TypeError, ValueError):
        return None
    if w <= 0.01 or h <= 0.01:
        return None
    x, y = clamp(x), clamp(y)
    return (x, y, clamp(w, 0.02, 1.0 - x), clamp(h, 0.02, 1.0 - y))


def to_pixels(rect, area) -> tuple[int, int, int, int]:
    left, top, width, height = area
    x, y, w, h = rect
    return (int(round(left + x * width)), int(round(top + y * height)),
            max(1, int(round(w * width))), max(1, int(round(h * height))))


def to_fractions(pixels, area) -> tuple[float, float, float, float]:
    left, top, width, height = area
    x, y, w, h = pixels
    if not width or not height:
        return (0.0, 0.0, 1.0, 1.0)
    return (clamp((x - left) / width), clamp((y - top) / height),
            clamp(w / width, 0.02, 1.0), clamp(h / height, 0.02, 1.0))


def nearest_preset(rects) -> tuple[str, float, float]:
    count = len(rects)
    if count <= 1:
        return "full", DEFAULT_SPLIT, DEFAULT_VSPLIT
    split = clamp(max(r[2] for r in rects), MIN_SPLIT, MAX_SPLIT)
    if count == 2:
        return "half", split, DEFAULT_VSPLIT
    if count >= 4:
        return "grid4", split, DEFAULT_VSPLIT
    return "6040", split, DEFAULT_VSPLIT
