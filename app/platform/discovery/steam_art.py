"""Locates a Steam game's icon and library artwork on disk, falling
back to Steam's CDN (with a circuit breaker) when the local cache
doesn't have it yet."""

from __future__ import annotations

import glob
import os
import re
import threading

from ...infra import log
from . import steam_paths

_STEAM_ART_NAMES = (
    "capsule_616x353.jpg",
    "header.jpg",
    "library_hero.jpg",
    "capsule_231x87.jpg",
)

_STEAM_PORTRAIT_HINTS = ("600x900", "library_600x900", "portrait")

_STEAM_CDN_HOSTS = ("cdn.cloudflare.steamstatic.com", "cdn.akamai.steamstatic.com")

_STEAM_CDN_ART = ("capsule_616x353.jpg", "header.jpg")

_CDN_TIMEOUT = 4

_CDN_MAX_BYTES = 8 * 1024 * 1024

_CDN_MAX_FAILURES = 3

_cdn_lock = threading.Lock()

_cdn_failures = 0

_cdn_misses: set[str] = set()

def _cdn_available() -> bool:
    with _cdn_lock:
        return _cdn_failures < _CDN_MAX_FAILURES

def _cdn_record(reachable: bool) -> None:
    global _cdn_failures
    with _cdn_lock:
        if reachable:
            _cdn_failures = 0
            return
        _cdn_failures += 1
        tripped = _cdn_failures == _CDN_MAX_FAILURES
    if tripped:
        log.warning("Steam CDN недоступен, пропуск загрузки изображений")

def _cdn_missed(key: str) -> bool:
    with _cdn_lock:
        return key in _cdn_misses

def _cdn_mark_missed(key: str) -> None:
    with _cdn_lock:
        _cdn_misses.add(key)

def reset_cdn_state() -> None:
    global _cdn_failures
    with _cdn_lock:
        _cdn_failures = 0
        _cdn_misses.clear()

def _http_get(url: str, timeout: int = _CDN_TIMEOUT) -> bytes | None:
    import urllib.error
    import urllib.request

    req = urllib.request.Request(url, headers={"User-Agent": "Centurio"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read(_CDN_MAX_BYTES + 1)
    except urllib.error.HTTPError:
        _cdn_record(True)
        return None
    except Exception:
        _cdn_record(False)
        return None
    _cdn_record(True)
    return None if len(data) > _CDN_MAX_BYTES else data

def _steam_cdn_art(appid: str, icon_cache: str | None) -> str | None:
    if not icon_cache:
        return None
    out = os.path.join(icon_cache, f"steam_{appid}_capsule.jpg")
    if os.path.exists(out):
        return out
    key = f"art:{appid}"
    if _cdn_missed(key) or not _cdn_available():
        return None
    for name in _STEAM_CDN_ART:
        for host in _STEAM_CDN_HOSTS:
            if not _cdn_available():
                return None
            data = _http_get(f"https://{host}/steam/apps/{appid}/{name}")
            if data and len(data) >= 1024:
                try:
                    os.makedirs(icon_cache, exist_ok=True)
                    with open(out, "wb") as fh:
                        fh.write(data)
                    return out
                except OSError:
                    return None
    _cdn_mark_missed(key)
    return None

def _steam_logo(cache: str, sub: str, appid: str) -> str | None:
    for p in (os.path.join(cache, f"{appid}_logo.png"), os.path.join(sub, "logo.png")):
        if os.path.exists(p):
            return p
    return None

def _steam_icon(root: str, appid: str, icon_cache: str | None = None) -> tuple[str | None, str]:

    cache = os.path.join(root, "appcache", "librarycache")
    sub = os.path.join(cache, str(appid))
    for name in _STEAM_ART_NAMES:
        for p in (os.path.join(cache, f"{appid}_{name}"), os.path.join(sub, name)):
            if os.path.exists(p):
                return p, "cover"
    if os.path.isdir(sub):
        imgs = glob.glob(os.path.join(sub, "*.jpg")) + glob.glob(os.path.join(sub, "*.png"))
        art = [p for p in imgs if os.path.isfile(p) and not any(
            k in os.path.basename(p).lower()
            for k in ("icon", "logo", *_STEAM_PORTRAIT_HINTS))]
        if art:
            return max(art, key=lambda p: os.path.getsize(p)), "cover"
    dl = _steam_cdn_art(appid, icon_cache)
    if dl:
        return dl, "cover"
    logo = _steam_logo(cache, sub, appid)
    if logo:
        return logo, "logo"
    icon = os.path.join(cache, f"{appid}_icon.jpg")
    if os.path.exists(icon):
        return icon, "contain"
    return None, "contain"

_STEAM_PORTRAIT_NAMES = ("library_600x900_2x.jpg", "library_600x900.jpg")

def _steam_portrait(root: str, appid: str, icon_cache: str | None = None) -> str | None:
    cache = os.path.join(root, "appcache", "librarycache")
    sub = os.path.join(cache, str(appid))
    for name in _STEAM_PORTRAIT_NAMES:
        for p in (os.path.join(cache, f"{appid}_{name}"), os.path.join(sub, name)):
            if os.path.exists(p):
                return p
    return _steam_cdn_portrait(appid, icon_cache)

def _steam_cdn_portrait(appid: str, icon_cache: str | None) -> str | None:
    if not icon_cache:
        return None
    out = os.path.join(icon_cache, f"steam_{appid}_portrait.jpg")
    if os.path.exists(out):
        return out
    key = f"portrait:{appid}"
    if _cdn_missed(key) or not _cdn_available():
        return None
    for name in _STEAM_PORTRAIT_NAMES:
        for host in _STEAM_CDN_HOSTS:
            if not _cdn_available():
                return None
            data = _http_get(f"https://{host}/steam/apps/{appid}/{name}")
            if data and len(data) >= 1024:
                try:
                    os.makedirs(icon_cache, exist_ok=True)
                    with open(out, "wb") as fh:
                        fh.write(data)
                    return out
                except OSError:
                    return None
    _cdn_mark_missed(key)
    return None

def poster_for(path: str, icon_cache: str | None = None) -> str | None:
    m = re.match(r"steam://rungameid/(\d+)", path or "")
    if not m:
        return None
    appid = m.group(1)
    for root in steam_paths._steam_roots():
        p = _steam_portrait(root, appid, icon_cache)
        if p:
            return p
    return _steam_cdn_portrait(appid, icon_cache)
