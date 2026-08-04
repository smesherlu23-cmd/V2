from __future__ import annotations

import threading

import flet as ft

from . import colors as C
from ..infra import log
from .format import T

PLAIN_SECONDS = 2.6
UNDO_SECONDS = 8
BOTTOM = 70
BOTTOM_LIFTED = 96


class ToastHost:
    def __init__(self, page: ft.Page):
        self.page = page
        self._lock = threading.RLock()
        self._timer: threading.Timer | None = None
        self._token = 0
        self._left = 0
        self._action = None

        self.icon = ft.Icon(ft.Icons.CHECK, size=18, color=C.GREEN)
        self.text = T("", size=13, color=C.TEXT, max_lines=2,
                      overflow=ft.TextOverflow.ELLIPSIS)
        self.detail = T("", size=11.5, color=C.MUTED, max_lines=2, visible=False,
                        overflow=ft.TextOverflow.ELLIPSIS)
        self.body = ft.Column([self.text, self.detail], spacing=3, expand=True, tight=True)
        self.action_label = T("", size=12.5, weight=ft.FontWeight.W_600, color=C.TEXT)
        self.action_btn = ft.Container(
            self.action_label, visible=False, padding=ft.padding.only(0, 0, 0, 2),
            border=ft.border.only(bottom=ft.BorderSide(1, C.TEXT_FAINT)),
            on_click=lambda e: self.fire_action())
        self.countdown = T("", size=10.5, color=C.MUTED_2, font_family="monospace", visible=False)

        self.card = ft.Container(
            ft.Row([self.icon, self.body, self.action_btn, self.countdown],
                   spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                   tight=True),
            bgcolor=C.TOAST_BG, border=ft.border.all(1, C.TOAST_BORDER),
            border_radius=12, padding=ft.padding.symmetric(13, 16), shadow=ft.BoxShadow(blur_radius=50, spread_radius=0,
                                            offset=ft.Offset(0, 20), color=C.SHADOW_TOAST),
            animate_opacity=ft.Animation(C.ANIM_FAST, ft.AnimationCurve.EASE_OUT),
        )
        self.control = ft.Container(self.card, left=0, bottom=BOTTOM, visible=False)

    def lift(self, above: bool):
        self.control.bottom = BOTTOM_LIFTED if above else BOTTOM
        self.recenter()

    def recenter(self):
        win = getattr(self.page, "window", None)
        window_w = getattr(win, "width", None) or C.LIBRARY_W
        width = self.card.width or C.TOAST_MIN_W
        self.control.left = max(8.0, (window_w - width) / 2)

    def show(self, text: str, icon=ft.Icons.CHECK, icon_color=C.GREEN,
             action=None, action_label: str | None = None, error: bool = False,
             detail: str | None = None):
        with self._lock:
            self._cancel_timer()
            self._token += 1
            token = self._token
            self._action = action
            self._left = UNDO_SECONDS if action else 0

            self.icon.name = ft.Icons.ERROR_OUTLINE if error else icon
            self.icon.color = C.DANGER if error else icon_color
            self.text.value = text
            self.detail.value = detail or ""
            self.detail.visible = bool(detail)
            self.card.bgcolor = C.ERR_BG if error else C.TOAST_BG
            self.card.border = ft.border.all(1, C.ERR_BORDER if error else C.TOAST_BORDER)
            self.action_btn.visible = bool(action)
            self.action_label.value = action_label or "Вернуть"
            self.countdown.visible = bool(action)
            self.countdown.value = str(self._left) if action else ""
            self.card.width = (C.TOAST_MIN_W if len(text) <= 48 and not detail
                               else C.TOAST_MAX_W)
            self.recenter()
            self.control.visible = True
            self._arm(1.0 if action else PLAIN_SECONDS, token)
        self._safe_update()

    def error(self, text: str, action=None, action_label: str | None = None,
              detail: str | None = None):
        self.show(text, error=True, action=action, action_label=action_label, detail=detail)

    def fire_action(self):
        with self._lock:
            action = self._action
            self._action = None
            self._cancel_timer()
            self.control.visible = False
        self._safe_update()
        if action:
            try:
                action()
            except Exception:
                log.exception("отменить тост не удалось")

    def dismiss(self):
        with self._lock:
            self._cancel_timer()
            self._action = None
            self.control.visible = False
        self._safe_update()

    def stop(self):
        with self._lock:
            self._cancel_timer()
            self._action = None

    def _arm(self, delay: float, token: int):
        timer = threading.Timer(delay, self._tick, args=(token,))
        timer.daemon = True
        self._timer = timer
        timer.start()

    def _cancel_timer(self):
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def _tick(self, token: int):
        with self._lock:
            if token != self._token:
                return
            self._timer = None
            if not self._action:
                self.control.visible = False
            else:
                self._left -= 1
                if self._left <= 0:
                    self._action = None
                    self.control.visible = False
                else:
                    self.countdown.value = str(self._left)
                    self._arm(1.0, token)
        self._safe_update()

    def _safe_update(self):
        try:
            if self.control.page:
                self.control.update()
        except Exception:
            log.exception("сбой при обновлении тоста")
