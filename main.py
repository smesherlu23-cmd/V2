from __future__ import annotations

import os
import sys

import flet as ft

from app.infra import log
from app.main import ASSETS_DIR, main
from app.platform import single_instance


def _notify_already_running():
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            None, "Centurio уже запущен — смотрите в трее.", "Centurio", 0x40)
    except Exception:
        pass


if __name__ == "__main__":
    log.install_excepthook()
    web = os.environ.get("CENTURIO_WEB") == "1"
    port = int(os.environ.get("CENTURIO_PORT", "0") or 0)
    if not web and not single_instance.acquire():
        _notify_already_running()
        sys.exit(0)
    if web:
        ft.app(target=main, view=None, port=port or 8550, assets_dir=str(ASSETS_DIR))
    else:
        ft.app(target=main, assets_dir=str(ASSETS_DIR))
