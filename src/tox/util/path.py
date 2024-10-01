from __future__ import annotations

from shutil import rmtree
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

CACHEDIR_TAG_CONTENT = b"""Signature: 8a477f597d28d172789f06886806bc55
# This file is a cache directory tag created by the Tox automation project (https://tox.wiki/).
# For information about cache directory tags, see:
#	http://www.brynosaurus.com/cachedir/
"""


def ensure_empty_dir(path: Path, except_filename: str | None = None) -> None:
    if path.exists():
        if path.is_dir():
            for sub_path in path.iterdir():
                if sub_path.name == except_filename:
                    continue
                if sub_path.is_dir():
                    rmtree(sub_path, ignore_errors=True)
                else:
                    sub_path.unlink()
        else:
            path.unlink()
            path.mkdir()
    else:
        path.mkdir(parents=True)


def ensure_cachedir_dir(path: Path) -> None:
    """
    Ensure that the given path is a directory, exists and
    contains a `CACHEDIR.TAG` file.
    """
    path.mkdir(parents=True, exist_ok=True)
    cachetag = path / "CACHEDIR.TAG"
    if not cachetag.is_file():
        cachetag.write_bytes(CACHEDIR_TAG_CONTENT)


__all__ = [
    "ensure_cachedir_dir",
    "ensure_empty_dir",
]
