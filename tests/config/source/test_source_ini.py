from __future__ import annotations

from pathlib import Path

from tox.config.loader.section import Section
from tox.config.source.ini import IniSource


def test_source_ini_with_interpolated(tmp_path: Path) -> None:
    loader = IniSource(tmp_path, content="[tox]\na = %(c)s").get_loader(Section(None, "tox"), {})
    assert loader is not None
    loader.load_raw("a", None, None)
