"""Point the project's :PEP:`832` ``.venv`` redirect file at a tox environment."""

from __future__ import annotations

import logging
import os
import secrets
import stat
import sys
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import IO, TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)
_FILE_NAME: Final[str] = ".venv"


def venv_redirect_path(root: Path) -> Path:
    return root / _FILE_NAME


def record_venv_redirect(root: Path, env: Path, is_ours: Callable[[Path], bool]) -> None:
    file: Final[Path] = root / _FILE_NAME
    try:
        with _open_dir(root) as dir_fd:
            # A foreign redirect or directory belongs to the user or another tool.
            if _mode(file, dir_fd) is not None and (
                (target := _redirect_target(file, dir_fd)) is None or target == env or not is_ours(target)
            ):
                return
            line: Final[str] = env.relative_to(root).as_posix() if env.is_relative_to(root) else str(env)
            _write_redirect(file, dir_fd, f"{line}\n")
    except OSError as exc:
        _LOGGER.warning("could not point %s at %s: %s", file, env, exc)


@contextmanager
def _open_dir(directory: Path) -> Generator[int | None, None, None]:
    # Pin each component so a link swapped in before an open cannot redirect it.
    if sys.platform == "win32":  # pragma: win32 cover  # Windows has no directory-relative file operations.
        yield None
    else:  # pragma: win32 no cover
        dir_fd = os.open(directory.anchor or ".", os.O_RDONLY | os.O_DIRECTORY)
        try:
            for component in directory.parts[1:] if directory.is_absolute() else directory.parts:
                next_fd = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=dir_fd)
                os.close(dir_fd)
                dir_fd = next_fd
            yield dir_fd
        finally:
            os.close(dir_fd)


def _mode(file: Path, dir_fd: int | None) -> int | None:
    try:
        return (file.lstat() if dir_fd is None else os.stat(file.name, dir_fd=dir_fd, follow_symlinks=False)).st_mode
    except OSError:
        return None


def _redirect_target(file: Path, dir_fd: int | None) -> Path | None:
    if (mode := _mode(file, dir_fd)) is None or not stat.S_ISREG(mode):
        return None
    try:
        with _open(file, dir_fd) as handler:
            return Path(os.path.normpath(file.parent / handler.read().removesuffix("\n")))
    except (OSError, UnicodeDecodeError):  # not a redirect file tox can read, so not one tox wrote
        return None


def _open(file: Path, dir_fd: int | None) -> IO[str]:
    if sys.platform == "win32":  # pragma: win32 cover  # Windows opens by path.
        return file.open(encoding="utf-8")

    def opener(path: str, flags: int) -> int:
        # Refuse a link swapped in after the metadata check.
        return os.open(path, flags | os.O_NOFOLLOW, dir_fd=dir_fd)

    return open(file.name, encoding="utf-8", opener=opener)


def _write_redirect(file: Path, dir_fd: int | None, text: str) -> None:
    if sys.platform == "win32":  # pragma: win32 cover  # Windows has no directory-relative replacement.
        file.write_text(text, encoding="utf-8")
        return
    name: Final[str] = f".{_FILE_NAME}.{secrets.token_hex(16)}"
    descriptor: Final[int] = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644, dir_fd=dir_fd)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handler:
            handler.write(text)
        # Replacement cannot follow a link or truncate a hard link swapped in after the read.
        os.replace(name, file.name, src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
    finally:
        with suppress(FileNotFoundError):
            os.unlink(name, dir_fd=dir_fd)


def forget_venv_redirect(root: Path, env: Path) -> None:
    try:
        with _open_dir(root) as dir_fd:
            file: Final[Path] = root / _FILE_NAME
            if _redirect_target(file, dir_fd) == env:
                # PEP 832 rejects an empty redirect, so remove it while the environment is rebuilt.
                _unlink(file, dir_fd)
    except (FileNotFoundError, NotADirectoryError):  # no root, so no redirect
        pass


def _unlink(file: Path, dir_fd: int | None) -> None:
    if dir_fd is None:  # pragma: win32 cover  # Windows has no directory descriptor.
        file.unlink(missing_ok=True)
    else:
        with suppress(FileNotFoundError):
            os.unlink(file.name, dir_fd=dir_fd)


def release_venv_redirect(path: Path, is_ours: Callable[[Path], bool]) -> bool:
    try:
        with _open_dir(path.parent) as dir_fd:
            if (target := _redirect_target(path, dir_fd)) is None or not is_ours(target):
                return False
            _unlink(path, dir_fd)
    except (FileNotFoundError, NotADirectoryError):  # no directory, so no redirect
        return False
    return True


__all__ = [
    "forget_venv_redirect",
    "record_venv_redirect",
    "release_venv_redirect",
    "venv_redirect_path",
]
