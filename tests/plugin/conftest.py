from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

HERE = Path(__file__).parent


def pytest_collection_modifyitems(items: Sequence[Any]) -> None:
    """automatically apply plugin test to all the test in this suite"""
    root = str(HERE)
    for item in items:
        if item.module.__file__.startswith(root):
            item.add_marker("plugin_test")
