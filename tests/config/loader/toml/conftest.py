from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

import pytest
import tomllib

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def mk_toml_conf(tmp_path: Path) -> Callable[[str], dict[str, Any]]:
    def _func(raw: str) -> dict[str, Any]:
        filename = tmp_path / "demo.toml"
        filename.write_bytes(raw.encode("utf-8"))  # win32: avoid CR normalization - what you pass is what you get
        with filename.open("rb") as file_handler:
            return tomllib.load(file_handler)

    return _func
