from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

from tox.config.types import MissingRequiredConfigKeyError

from .ini import IniSource

if TYPE_CHECKING:
    from pathlib import Path


class LegacyToml(IniSource):
    FILENAME = "pyproject.toml"

    def __init__(self, path: Path) -> None:
        if path.name != self.FILENAME or not path.exists():
            raise ValueError
        # editors on Windows may prepend a BOM, which tomllib would reject
        toml_content = tomllib.loads(path.read_text(encoding="utf-8-sig"))
        try:
            content = toml_content["tool"]["tox"]["legacy_tox_ini"]
        except (KeyError, TypeError) as exc:  # TypeError when tool or tool.tox is not a table
            msg = f"`tool.tox.legacy_tox_ini` missing from {path}"
            raise MissingRequiredConfigKeyError(msg) from exc
        super().__init__(path, content=content)


__all__ = ("LegacyToml",)
