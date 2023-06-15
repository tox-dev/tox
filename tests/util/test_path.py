from __future__ import annotations

from typing import TYPE_CHECKING

from tox.util.path import ensure_empty_dir

if TYPE_CHECKING:
    from pathlib import Path


def test_ensure_empty_dir_file(tmp_path: Path) -> None:
    dest = tmp_path / "a"
    dest.write_text("")
    ensure_empty_dir(dest)
    assert dest.is_dir()
    assert not list(dest.iterdir())
