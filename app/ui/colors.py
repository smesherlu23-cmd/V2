from __future__ import annotations

import colorsys
import re

BG_0 = "#08080a"
BG_1 = "#0b0b0d"
BG_2 = "#0a0a0c"
PANEL = "#111114"
PANEL_2 = "#141417"
PANEL_3 = "#17171b"
LINE = "#212126"
LINE_2 = "#17171b"
LINE_4 = "#2c2c33"
LINE_5 = "#33333a"
TEXT = "#e6e6e8"
TEXT_2 = "#c8ccd0"
MUTED = "#9aa0a6"
MUTED_2 = "#6b6b70"
MUTED_3 = "#3d3d43"
GREEN = "#4ade80"
DANGER = "#e34f4f"
STAR = "#f5c518"

CONTROL = "#23232b"          
RAIL_BTN_BG = "#101014"      

ACCENT = "#f5f5f7"          
ON_ACCENT = "#0b0b0d"        
WHITE = "#ffffff"           

SLOT_BG = "#15151b"
SLOT_BORDER = "#26262e"
SLOT_GLYPH = "#7f8590"

TEXT_DIM = "#5a5f68"      
TEXT_FAINT = "#4a4f58"       
TEXT_GHOST = "#2e2e37"       
HINT = "#33383f"             
WINDOW_BORDER = "#23232b"    
PANEL_ACTIVE = "#1e1e22"     
DASHED_RAIL = "#3a3a44"      
MATCH_BG = "#2b2b33"         
TOGGLE_OFF = "#2a2a30"       
DOT = "#43434c"              
SEGMENT_BORDER = "#1e1e25"   
PROGRESS_TRACK = "#1a1a21"   
SLOT_BORDER_SEL = "#2e2e38"  
SLOT_GLYPH_SEL = "#8f959f"

SELECTED_BG = "#141418"      
MENU_BORDER = "#2c2c33"
TOAST_BG = "#17171b"
TOAST_BORDER = "#2e2e38"

BADGE_BG = "#0c100e"        
BADGE_BORDER = "#2a5f42"
BADGE_TEXT = "#d8fce6"
GREEN_TEXT = "#7ee2a8"

ERR_TEXT = "#ee8888"
ERR_BG = "#1a1113"
ERR_BORDER = "#3a2222"
ERR_BTN_BORDER = "#5a2a2a"

SET_BG = "#0e0e12"
SET_BORDER = "#1c1c23"
SET_SLOT_BG = "#131318"
SET_SLOT_BORDER = "#202028"
DASHED = "#1f1f27"           

PALETTE_BG = "#101015"
PALETTE_BORDER = "#2a2a33"
PALETTE_FOOT = "#0c0c10"
PALETTE_FOOT_BORDER = "#1c1c23"
PALETTE_ROW = "#1c1c23"       
SCRIM_BODY = "#99050507"      
SHADOW_PALETTE = "#cc000000"  
FIELD_ACTIVE_BG = "#15151c"
FIELD_ACTIVE_BORDER = "#4a4f58"

BAR_BG = "#16161d"
BAR_BORDER = "#33333a"
BAR_BTN = "#1f1f27"
SHADOW_BAR = "#a6000000"      

CANVAS_BG = "#0e0e12"
PRESET_ACTIVE_BG = "#16161c"   
WIN_BG = "#15151d"
WIN_BORDER = "#2c2c36"
WIN_BORDER_ACTIVE = "#3a3a44"

TRIAGE_SLOT_BORDER = "#2a2a33"
TRIAGE_PICK_BG = "#141418"
TRIAGE_PICK_BORDER = "#33333a"
TRIAGE_CHIP_BORDER = "#212128"
DONE_BG = "#0e130f"
DONE_BORDER = "#244530"

TRANSPARENT = "#00000000"
SCRIM = "#dd0c0c0e"          
OVERLAY = "#99050506"        
SHADOW_MENU = "#b3000000"   
SHADOW_TOAST = "#99000000"   

CAT_PALETTE = ("#e6e6e8", "#f5c518", "#f0a020", "#e34f4f",
               "#b06cf0", "#4f7dff", "#3ecfaf", "#7a8290",
               "#b98cff", "#ff9f6e")
ACCENT_CHOICES = ("#f5f5f7", "#4f7dff", "#3ecfaf", "#f0a020")

TILE_GRADIENT = ("#191920", "#111116")
TILE_GRADIENT_SEL = ("#1d1d26", "#141419")
POSTER_SCRIM = ("#00000000", "#e8000000")
HUE_STRIP = ("#e34f4f", "#f0a020", "#f5c518", "#4ade80",
             "#3ecfaf", "#4f7dff", "#b06cf0", "#e34f4f")

HEADER_H = 52
RAIL_W = 72
RAIL_BTN = 42
SIDEBAR_W = 232
INSPECTOR_W = 300
SEARCH_W = 560
SEARCH_MIN_W = 220
PALETTE_W = 640
TILE_W = 164
TILE_W_COMPACT = 140
TILE_COVER_H = 90
TILE_COVER_H_COMPACT = 78
TILE_SLOT = 50
TILE_SLOT_COMPACT = 42
QUICK_W = 132
POSTER_W = 132
POSTER_H = 198
POSTER_W_COMPACT = 112
POSTER_H_COMPACT = 168
LIBRARY_W = 1400
LIBRARY_H = 880
LIBRARY_MIN_W = 940
LIBRARY_MIN_H = 620
MENU_W = 300
POPOVER_W = 330
POPOVER_H = 486       
TOAST_MIN_W = 360
TOAST_MAX_W = 520
SET_SIDE_W = 300      
SETTINGS_NAV_W = 200  
CANVAS_H = 280       

NARROW_INSPECTOR = 1200
NARROW_SIDEBAR = 1000

ANIM_FAST = 120
ANIM_HOVER = 80
ANIM_BAR = 140


def _hex(rgb) -> str:
    r, g, b = rgb
    return "#%02x%02x%02x" % (max(0, min(255, round(r * 255))),
                              max(0, min(255, round(g * 255))),
                              max(0, min(255, round(b * 255))))


def cover_colors(hue: int) -> tuple[str, str]:
    h = (hue % 360) / 360.0
    top = colorsys.hls_to_rgb(h, 0.58, 0.62)
    bottom = colorsys.hls_to_rgb(h, 0.42, 0.60)
    return _hex(top), _hex(bottom)


def chip_colors(hue: int) -> tuple[str, str]:
    h = (hue % 360) / 360.0
    top = colorsys.hls_to_rgb(h, 0.62, 0.62)
    bottom = colorsys.hls_to_rgb(h, 0.48, 0.60)
    return _hex(top), _hex(bottom)


def glyph_color(hue: int) -> str:
    h = (hue % 360) / 360.0
    r, g, b = colorsys.hls_to_rgb(h, 0.55, 0.61)
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return BG_1 if luminance > 0.6 else "#ffffff"


def parse_hex(text) -> str | None:
    if not text:
        return None
    s = str(text).strip().lower()
    m = re.match(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$", s)
    if not m:
        m = re.match(r"(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})$", s)
    if m:
        return rgb_to_hex(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    s = s.lstrip("#")
    if len(s) == 3 and all(c in "0123456789abcdef" for c in s):
        s = "".join(c * 2 for c in s)
    if len(s) == 6 and all(c in "0123456789abcdef" for c in s):
        return "#" + s
    return None


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = (parse_hex(hex_color) or "#888888").lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def rgb_to_hex(r: int, g: int, b: int) -> str:
    clamp = lambda v: max(0, min(255, int(v)))
    return "#%02x%02x%02x" % (clamp(r), clamp(g), clamp(b))


def with_alpha(hex_color: str, alpha: float) -> str:
    base = (parse_hex(hex_color) or "#000000").lstrip("#")
    return "#%02x%s" % (max(0, min(255, round(alpha * 255))), base)


def hsl_to_hex(hue: float, lightness: float, saturation: float = 0.62) -> str:
    r, g, b = colorsys.hls_to_rgb((hue % 360) / 360.0,
                                  max(0.0, min(1.0, lightness)),
                                  max(0.0, min(1.0, saturation)))
    return _hex((r, g, b))


def hex_to_hsl(hex_color: str) -> tuple[float, float, float]:
    r, g, b = (v / 255 for v in hex_to_rgb(hex_color))
    h, lightness, s = colorsys.rgb_to_hls(r, g, b)
    return h * 360, lightness, s


def category_color(cat: dict) -> str:
    return parse_hex(cat.get("color")) or WHITE
