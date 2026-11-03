from __future__ import annotations

import logging
import os
import shutil
import stat
import sys
from contextlib import ExitStack
from os.path import commonpath
from typing import TYPE_CHECKING, Final

from tox.util.path import ensure_private_dir

if TYPE_CHECKING:
    from pathlib import Path


def create_session_view(
    package: Path, temp_path: Path, trust_root: Path | None = None, work_dir: Path | None = None
) -> Path:
    if temp_path.is_symlink():
        temp_path.unlink()
    ensure_private_dir(temp_path)
    if sys.platform != "win32":
        user_id: Final[int] = os.geteuid()
        if trust_root is not None and work_dir is not None:
            _repair_owned_staging_path(temp_path, trust_root, work_dir, user_id)
        _ensure_private_staging_path(temp_path, trust_root, user_id)
    file_id: Final[int] = max((int(entry.name) for entry in temp_path.iterdir() if entry.name.isnumeric()), default=0)
    session_dir: Final[Path] = temp_path / str(file_id + 1)
    session_dir.mkdir(mode=0o700)
    session_package: Final[Path] = session_dir / package.name

    with package.open("rb") as source, session_package.open("xb") as target:
        shutil.copyfileobj(source, target)
    try:
        common = commonpath((session_package, package))
    except ValueError:  # no shared base (e.g. different Windows drives); only the debug log needs it
        logging.debug("package copied from %s to %s", package, session_package)
    else:
        rel_session, rel_package = session_package.relative_to(common), package.relative_to(common)
        logging.debug("package %s copied to %s (%s)", rel_session, rel_package, common)
    return session_package


def _repair_owned_staging_path(temp_path: Path, trust_root: Path, work_dir: Path, user_id: int) -> None:
    try:
        work_parts: Final[tuple[str, ...]] = work_dir.relative_to(trust_root).parts
        staging_parts: Final[tuple[str, ...]] = temp_path.relative_to(work_dir).parts
    except ValueError:
        return
    if ".." in {*work_parts, *staging_parts}:
        return

    directory_flag: Final[int | None] = getattr(os, "O_DIRECTORY", None)
    nofollow_flag: Final[int | None] = getattr(os, "O_NOFOLLOW", None)
    if directory_flag is None or nofollow_flag is None:
        return
    flags: Final[int] = os.O_RDONLY | directory_flag | nofollow_flag
    with ExitStack() as stack:
        directory: int = os.open(trust_root.resolve(), flags)
        stack.callback(os.close, directory)
        owned: Final[list[tuple[int, int]]] = []
        entries: Final[list[tuple[int, str, int, Path]]] = []
        parts: Final[tuple[str, ...]] = (*work_parts, *staging_parts)
        for index, part in enumerate(parts):
            try:
                child = os.open(part, flags, dir_fd=directory)
            except OSError:
                return
            entries.append((directory, part, child, trust_root.joinpath(*parts[: index + 1])))
            directory = child
            stack.callback(os.close, directory)
            metadata: os.stat_result = os.fstat(directory)
            if metadata.st_uid != user_id or metadata.st_mode & stat.S_IWOTH:
                return
            if index >= len(work_parts) - 1:
                owned.append((directory, stat.S_IMODE(metadata.st_mode)))
            elif metadata.st_mode & stat.S_IWGRP:
                return

        _remove_group_write(owned)
        _verify_unchanged_staging_path(entries)


def _remove_group_write(directories: list[tuple[int, int]]) -> None:
    for descriptor, mode in directories:
        if mode & stat.S_IWGRP:
            os.fchmod(descriptor, mode & ~stat.S_IWGRP)


def _verify_unchanged_staging_path(entries: list[tuple[int, str, int, Path]]) -> None:
    for parent, name, child, path in entries:
        msg: str = f"package staging path {path} can be changed by another account"
        try:
            current: os.stat_result = os.stat(name, dir_fd=parent, follow_symlinks=False)
        except OSError as exc:
            raise PermissionError(msg) from exc
        original: os.stat_result = os.fstat(child)
        if (current.st_dev, current.st_ino) != (original.st_dev, original.st_ino):
            raise PermissionError(msg)


def _ensure_private_staging_path(temp_path: Path, trust_root: Path | None, user_id: int) -> None:
    trusted_roots: Final[set[Path]] = {trust_root, trust_root.resolve()} if trust_root is not None else set()
    for candidate in {temp_path, temp_path.resolve()}:
        for parent in (candidate, *candidate.parents):
            if parent in trusted_roots:
                break
            metadata: os.stat_result = parent.stat()
            mutable_link: bool = (
                parent.is_symlink()
                and bool(parent.parent.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH))
                and parent.lstat().st_uid not in {0, user_id}
            )
            if (
                metadata.st_uid not in {0, user_id}
                or (metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH) and not metadata.st_mode & stat.S_ISVTX)
                or mutable_link
            ):
                msg: str = f"package staging path {parent} can be changed by another account"
                raise PermissionError(msg)


__all__ = [
    "create_session_view",
]
