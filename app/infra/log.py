from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from . import paths

_LOGGER = logging.getLogger("centurio")
_LOGGER.addHandler(logging.NullHandler())
_configured = False


def is_debug() -> bool:
    return "--debug" in sys.argv or os.environ.get("CENTURIO_DEBUG") == "1"


def _default_dir() -> Path:
    return paths.data_dir()


def setup(debug: bool | None = None, log_dir: str | Path | None = None) -> logging.Logger:
    global _configured
    if _configured:
        return _LOGGER
    if debug is None:
        debug = is_debug()

    _LOGGER.setLevel(logging.DEBUG if debug else logging.WARNING)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")

    try:
        d = Path(log_dir) if log_dir else _default_dir()
        d.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(d / "centurio.log", maxBytes=512 * 1024,
                                 backupCount=3, encoding="utf-8")
        fh.setFormatter(fmt)
        _LOGGER.addHandler(fh)
    except Exception:
        pass

    if debug:
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        _LOGGER.addHandler(sh)

    _LOGGER.debug("logging started (log dir: %s)", log_dir or "<default>")

    _configured = True
    return _LOGGER

def install_excepthook() -> None:
    """Отправить необработанные исключения в лог.

    Собранное приложение живёт без консоли, поэтому исключение, до которого
    никто не дотянулся, убивает окно вообще без следа: ни текста, ни записи в
    centurio.log. Логгер настраиваем лениво, прямо в обработчике, — иначе
    ранний setup() перебил бы тот, что делает main() уже зная настройку
    debug_log из хранилища.
    """
    def _log(exc_type, exc, tb) -> None:
        try:
            setup()
        except Exception:
            pass
        _LOGGER.critical("необработанное исключение", exc_info=(exc_type, exc, tb))

    def _hook(exc_type, exc, tb) -> None:
        _log(exc_type, exc, tb)
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = _hook

    # Flet зовёт main() в отдельном потоке, туда sys.excepthook не достаёт.
    import threading

    def _thread_hook(args) -> None:
        _log(args.exc_type, args.exc_value, args.exc_traceback)

    threading.excepthook = _thread_hook


def debug(msg, *args, **kw):
    _LOGGER.debug(msg, *args, **kw)


def info(msg, *args, **kw):
    _LOGGER.info(msg, *args, **kw)


def warning(msg, *args, **kw):
    _LOGGER.warning(msg, *args, **kw)


def error(msg, *args, **kw):
    _LOGGER.error(msg, *args, **kw)


def exception(msg, *args, **kw):
    _LOGGER.exception(msg, *args, **kw)
