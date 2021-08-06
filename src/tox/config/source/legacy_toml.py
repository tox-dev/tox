from pathlib import Path

import tomli

from .ini import IniSource


class LegacyToml(IniSource):
    FILENAME = "pyproject.toml"

    def __init__(self, path: Path):
        if path.name != self.FILENAME or not path.exists():
            raise ValueError
        with path.open("rb") as file_handler:
            toml_content = tomli.load(file_handler)
        try:
            content = toml_content["tool"]["tox"]["legacy_tox_ini"]
        except KeyError:
            raise ValueError
        super().__init__(path, content=content)


__all__ = ("LegacyToml",)
