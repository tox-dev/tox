import importlib
import sys
from pathlib import Path
from types import ModuleType
from typing import Optional


def load_inline(path: Path) -> Optional[ModuleType]:
    # nox uses here the importlib.machinery.SourceFileLoader but I consider this similarly good, and we can keep any
    # name for the tox file, it's content will always be loaded in the this module from a system point of view
    for name in ("toxfile", "☣"):
        candidate = path.parent / f"{name}.py"
        if candidate.exists():
            return _load_plugin(candidate)
    return None


def _load_plugin(path: Path) -> ModuleType:
    in_folder = path.parent
    module_name = path.stem

    sys.path.insert(0, str(in_folder))
    try:
        if module_name in sys.modules:
            del sys.modules[module_name]  # pragma: no cover
        module = importlib.import_module(module_name)
        return module
    finally:
        del sys.path[0]
