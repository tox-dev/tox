from pathlib import Path

from .ini import IniSource


class SetupCfg(IniSource):
    """Configuration sourced from a tox.ini file"""

    CORE_PREFIX = "tox:tox"
    FILENAME = "setup.cfg"

    def __init__(self, path: Path):
        super().__init__(path)
        if not self._parser.has_section(self.CORE_PREFIX):
            raise ValueError


__all__ = ("SetupCfg",)
