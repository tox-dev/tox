from __future__ import annotations

from configparser import ConfigParser
from typing import TYPE_CHECKING, Callable

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def mk_ini_conf(tmp_path: Path) -> Callable[[str], ConfigParser]:
    def _func(raw: str) -> ConfigParser:
        filename = tmp_path / "demo.ini"
        filename.write_bytes(raw.encode("utf-8"))  # win32: avoid CR normalization - what you pass is what you get
        parser = ConfigParser(interpolation=None)
        with filename.open() as file_handler:
            parser.read_file(file_handler)
        return parser

    return _func
