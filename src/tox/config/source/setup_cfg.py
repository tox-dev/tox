from __future__ import annotations

from typing import TYPE_CHECKING

from tox.config.types import MissingRequiredConfigKeyError

from .ini import IniSource
from .ini_section import IniSection

if TYPE_CHECKING:
    from pathlib import Path


class SetupCfg(IniSource):
    """Configuration sourced from a setup.cfg file."""

    CORE_SECTION = IniSection("tox", "tox")
    FILENAME = "setup.cfg"

    def __init__(self, path: Path) -> None:
        super().__init__(path)
        if not self._parser.has_section(self.CORE_SECTION.key):
            raise MissingRequiredConfigKeyError(path)


__all__ = ("SetupCfg",)
