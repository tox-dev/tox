from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from collections.abc import Sequence


_HERE: Final[Path] = Path(__file__).parent


def pytest_collection_modifyitems(  # simplint: ignore[SMP602]  # pytest passes collected items of any type
    items: Sequence[Any],  # simplint: ignore[SMP602]  # pytest passes collected items of any type
) -> None:
    # automatically apply plugin test to all the test in this suite
    root = str(_HERE)
    for item in items:
        if item.module.__file__.startswith(root):
            item.add_marker("plugin_test")
