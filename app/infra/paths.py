from __future__ import annotations

import os
from pathlib import Path

APP_DIR_NAME = "Centurio"


def data_dir() -> Path:
    base = Path(os.environ.get("APPDATA") or Path.home())
    return base / APP_DIR_NAME
