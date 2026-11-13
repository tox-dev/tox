from __future__ import annotations

import os
import stat
import sys
from contextlib import suppress
from pathlib import Path
from shutil import rmtree
from typing import TYPE_CHECKING, Final, Protocol

if TYPE_CHECKING:
    from types import TracebackType


def ensure_cachedir_tag(work_dir: Path) -> None:
    """Ensure a ``CACHEDIR.TAG`` file exists in *work_dir* per https://bford.info/cachedir/spec.html.

    :param work_dir: the directory to create the tag in

    """
    tag_path = work_dir / "CACHEDIR.TAG"
    cachedir_tag = """\
Signature: 8a477f597d28d172789f06886806bc55
# This file is a cache directory tag created by tox.
# For information about cache directory tags, see:
#	https://bford.info/cachedir/spec.html
"""
    if not tag_path.exists():
        ensure_private_dir(work_dir)
        tag_path.write_text(cachedir_tag, encoding="utf-8")


def ensure_private_dir(path: Path) -> None:
    """Create a directory, and its parents, that only the current user can access.

    :param path: the directory to create

    """
    try:
        path.mkdir(mode=0o700, exist_ok=True)
    except FileNotFoundError:
        ensure_private_dir(path.parent)
        path.mkdir(mode=0o700, exist_ok=True)


def ensure_empty_dir(path: Path, except_filename: str | None = None) -> None:
    """Make sure a directory exists and is empty, removing its content.

    :param path: the directory to make empty
    :param except_filename: the name of a file to keep in the directory, ``None`` to keep none

    """
    if path.is_symlink():
        path.unlink()
    elif (
        sys.platform == "win32"
        and os.path.lexists(path)
        and getattr(path.lstat(), "st_reparse_tag", None) == getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", None)
    ):
        path.rmdir()
    if path.exists():
        if path.is_dir():
            directory_flag: Final[int | None] = getattr(os, "O_DIRECTORY", None)
            nofollow_flag: Final[int | None] = getattr(os, "O_NOFOLLOW", None)
            if rmtree.avoids_symlink_attacks and directory_flag is not None and nofollow_flag is not None:
                _empty_dir_fd(path, except_filename, directory_flag | nofollow_flag)
            else:
                _empty_dir_path(path, except_filename)
        else:
            path.unlink()
            path.mkdir()
    else:
        path.mkdir(parents=True)


def _empty_dir_fd(path: Path, except_filename: str | None, flags: int) -> None:
    dir_fd: Final = os.open(path, os.O_RDONLY | flags)
    try:
        with os.scandir(dir_fd) as scan:
            entries: Final = list(scan)
        for entry in entries:
            if entry.name == except_filename:
                continue
            if entry.is_dir(follow_symlinks=False):
                rmtree(entry.name, ignore_errors=True, dir_fd=dir_fd)
            else:
                os.unlink(entry.name, dir_fd=dir_fd)
    finally:
        os.close(dir_fd)


def _empty_dir_path(path: Path, except_filename: str | None) -> None:
    for sub_path in path.iterdir():
        if sub_path.name == except_filename:
            continue
        if sub_path.is_dir() and not sub_path.is_symlink():
            if sys.version_info >= (3, 12):  # pragma: >=3.12 cover
                rmtree(sub_path, onexc=_retry_unlink)
            else:  # pragma: <3.12 cover
                rmtree(sub_path, onerror=_retry_unlink)
        else:
            _unlink(sub_path)


def _retry_unlink(
    func: _FailedCall, path: str, _exc: BaseException | tuple[type[BaseException], BaseException, TracebackType | None]
) -> None:
    # rmtree also reports failed os.open, os.scandir and os.close calls; retrying those cannot help, so they stay behind
    if func is os.unlink:
        with suppress(OSError):
            _unlink(Path(path))


def _unlink(path: Path) -> None:
    try:
        path.unlink()
    except PermissionError:
        # Windows refuses to delete a read-only file; a symlink is left as is so its target keeps its mode
        if path.is_symlink() or path.stat().st_mode & stat.S_IWRITE:
            raise
        path.chmod(stat.S_IWRITE)
        path.unlink()


class _FailedCall(Protocol):
    def __call__(self, target: str | int, /) -> None: ...


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
    "ensure_private_dir",
]
