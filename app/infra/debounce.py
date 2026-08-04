from __future__ import annotations

import threading

class Debounce:
    def __init__(self, delay: float, fn):
        self.delay = delay
        self.fn = fn
        self._lock = threading.Lock()
        self._handle = None

    def _fire(self):
        with self._lock:
            self._handle = None
        self.fn()

    def schedule(self, immediate: bool = False) -> None:
        with self._lock:
            if self._handle is not None:
                self._handle.cancel()
                self._handle = None
            if not immediate:
                timer = threading.Timer(self.delay, self._fire)
                timer.daemon = True
                self._handle = timer
                timer.start()
        if immediate:
            self._fire()

    def cancel(self) -> None:
        with self._lock:
            if self._handle is not None:
                self._handle.cancel()
                self._handle = None
