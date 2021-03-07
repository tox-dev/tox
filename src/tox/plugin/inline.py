import sys
from pathlib import Path
from runpy import run_path
from types import ModuleType
from typing import Any, Dict, Optional


def load_inline(path: Path) -> Optional[ModuleType]:
    # nox uses here the importlib.machinery.SourceFileLoader but I consider this similarly good, and we can keep any
    # name for the tox file, it's content will always be loaded in the this module from a system point of view
    path = path.parent / "tox_.py"
    if path.exists():
        return _load_plugin(path)
    return None


def _load_plugin(path: Path) -> ModuleType:
    loaded_module: Dict[str, Any] = run_path(str(path), run_name="__tox__")  # type: ignore # python/typeshed - 4965
    for key, value in loaded_module.items():
        if not key.startswith("_"):
            globals()[key] = value
    return sys.modules[__name__]
