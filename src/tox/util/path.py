from __future__ import annotations

from shutil import rmtree
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_CACHEDIR_TAG = """\
Signature: 8a477f597d28d172789f06886806bc55
# This file is a cache directory tag created by tox.
# For information about cache directory tags, see:
#	https://bford.info/cachedir/spec.html
"""


def ensure_cachedir_tag(work_dir: Path) -> None:
    """Ensure a ``CACHEDIR.TAG`` file exists in *work_dir* per https://bford.info/cachedir/spec.html."""
    tag_path = work_dir / "CACHEDIR.TAG"
    if not tag_path.exists():
        work_dir.mkdir(parents=True, exist_ok=True)
        tag_path.write_text(_CACHEDIR_TAG, encoding="utf-8")


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


def ensure_gitignore(path: Path) -> None:
    """Create a ``.gitignore`` file with ``*`` in the given directory if one does not already exist.

    This prevents tox-managed directories (like ``.tox/``) from being tracked by git, so users don't need to add them to
    their project's ``.gitignore``.

    :param path: the directory in which to create the ``.gitignore`` file

    """
    if not (gitignore := path / ".gitignore").exists():
        path.mkdir(parents=True, exist_ok=True)
        gitignore.write_text("*\n", encoding="utf-8")


__all__ = [
    "ensure_cachedir_tag",
    "ensure_empty_dir",
    "ensure_gitignore",
]
