from __future__ import annotations

import sys
import threading

from ..infra import log

_ERROR_ALREADY_EXISTS = 183
MUTEX_NAME = "Global\\CenturioSingleInstanceMutex"

_handle = None
_lock = threading.Lock()


def acquire() -> bool:
    global _handle
    if not sys.platform.startswith("win"):
        return True
    with _lock:
        if _handle is not None:
            return True
        try:
            import ctypes
            handle = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
            if not handle:
                return True
            already = ctypes.windll.kernel32.GetLastError() == _ERROR_ALREADY_EXISTS
            if already:
                ctypes.windll.kernel32.CloseHandle(handle)
                return False
            _handle = handle
            return True
        except Exception:
            log.exception("не удалось проверить единственный экземпляр")
            return True


def release() -> None:
    global _handle
    with _lock:
        if _handle is None:
            return
        try:
            import ctypes
            ctypes.windll.kernel32.CloseHandle(_handle)
        except Exception:
            log.exception("не удалось освободить мьютекс единственного экземпляра")
        _handle = None
