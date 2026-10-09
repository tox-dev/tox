from __future__ import annotations

import stat
import sys
from pathlib import Path
from shutil import rmtree
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

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


def _make_writable(path: Path | str) -> None:
    entry = Path(path)
    entry.chmod(entry.stat().st_mode | stat.S_IWRITE)


def _remove_read_only(func: Callable[[str], object], path: str, _exc: object) -> None:
    """Clear the read-only bit and retry once, a second failure is ignored as ``ignore_errors=True`` did."""
    try:
        _make_writable(path)
        func(path)
    except OSError:
        pass


def ensure_empty_dir(path: Path, except_filename: str | None = None) -> None:
    if path.exists():
        if path.is_dir():
            for sub_path in path.iterdir():
                if sub_path.name == except_filename:
                    continue
                if sub_path.is_dir() and not sub_path.is_symlink():  # unlink a link, keep what it points to
                    if sys.version_info >= (3, 12):  # pragma: >=3.12 cover
                        rmtree(sub_path, onexc=_remove_read_only)
                    else:  # pragma: <3.12 cover
                        rmtree(sub_path, onerror=_remove_read_only)
                else:
                    try:
                        sub_path.unlink()
                    except PermissionError:  # a read-only file cannot be removed on Windows
                        _make_writable(sub_path)
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
