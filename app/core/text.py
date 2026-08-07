from __future__ import annotations

import time


def _plural(n, one, few, many):
    m10, m100 = n % 10, n % 100
    if m10 == 1 and m100 != 11:
        return one
    if 2 <= m10 <= 4 and not (10 <= m100 < 20):
        return few
    return many


def initials(name: str) -> str:
    n = (name or "?").strip()
    return n[0].upper() if n else "?"


def time_ago(ms: int) -> str:
    if not ms:
        return ""
    diff = time.time() * 1000 - ms
    m = int(diff // 60000)
    if m < 1:
        return "только что"
    if m < 60:
        return f"{m} {_plural(m, 'минуту', 'минуты', 'минут')} назад"
    h = m // 60
    if h < 24:
        return f"{h} {_plural(h, 'час', 'часа', 'часов')} назад"
    d = h // 24
    return f"{d} {_plural(d, 'день', 'дня', 'дней')} назад"


def short_ago(ms: int) -> str:
    if not ms:
        return ""
    diff = time.time() * 1000 - ms
    hours = int(diff // 3600000)
    if hours < 24:
        return "сегодня"
    days = hours // 24
    if days == 1:
        return "вчера"
    return f"{days} {_plural(days, 'день', 'дня', 'дней')} назад"


def plu_apps(n):
    return _plural(n, "приложение", "приложения", "приложений")


def plu_hits(n):
    return _plural(n, "совпадение", "совпадения", "совпадений")


def plu_programs(n):
    return _plural(n, "программа", "программы", "программ")


def plu_windows(n):
    return _plural(n, "окно", "окна", "окон")
