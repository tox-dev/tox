from pathlib import Path

import toml

from .ini import IniSource


class LegacyToml(IniSource):
    FILENAME = "pyproject.toml"

    def __init__(self, path: Path):
        if not path.exists():
            raise ValueError
        toml_content = toml.loads(path.read_text())
        try:
            content = toml_content["tool"]["tox"]["legacy_tox_ini"]
        except KeyError:
            raise ValueError
        super().__init__(path, content=content)


__all__ = ("LegacyToml",)
