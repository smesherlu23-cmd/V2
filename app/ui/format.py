from __future__ import annotations

import flet as ft

ICON_PACK = [
    "work", "business", "apartment", "store", "home", "folder", "folder_special",
    "code", "terminal", "data_object", "bug_report", "build", "engineering", "memory",
    "brush", "palette", "draw", "design_services", "architecture", "photo_camera",
    "image", "movie", "movie_creation", "music_note", "headphones", "mic", "podcasts",
    "sports_esports", "videogame_asset", "casino", "extension", "sports_soccer",
    "sports_basketball", "fitness_center", "directions_run", "chat", "mail", "forum",
    "language", "translate", "public", "map", "place", "flight", "directions_car",
    "school", "menu_book", "book", "science", "calculate", "functions",
    "cloud", "download", "storage", "dns", "wifi", "security", "lock", "vpn_key",
    "settings", "dashboard", "widgets", "apps", "star", "favorite", "bolt",
    "local_cafe", "restaurant", "shopping_cart", "attach_money", "credit_card",
    "calendar_month", "schedule", "alarm", "computer", "desktop_windows", "tv",
    "phone_android", "keyboard", "print", "rocket_launch", "pets", "spa",
]

_BOLD = {ft.FontWeight.BOLD, ft.FontWeight.W_700, ft.FontWeight.W_800, ft.FontWeight.W_900}


def _family_for(weight):
    if weight in _BOLD:
        return "Inter Bold"
    if weight == ft.FontWeight.W_600:
        return "Inter SemiBold"
    return "Inter"


def T(value="", **kw):
    fam = kw.get("font_family")
    if fam == "monospace":
        kw["font_family"] = "mono"
    elif fam is None:
        kw["font_family"] = _family_for(kw.get("weight"))
    return ft.Text(value, **kw)


def cat_icon(name: str):
    return getattr(ft.Icons, (name or "folder").upper(), ft.Icons.FOLDER)
