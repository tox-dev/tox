import sys
from pathlib import Path
from runpy import run_path
from types import ModuleType
from typing import Optional


def load_inline() -> Optional[ModuleType]:
    path = Path.cwd() / "tox_.py"
    if path.exists():
        for key, value in run_path(path, run_name="__tox__").items():
            if not key.startswith("_"):
                globals()[key] = value
        return sys.modules[__name__]
    return None
