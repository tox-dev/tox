from __future__ import annotations

import logging
import os
import shutil
import stat
import sys
from contextlib import ExitStack
from dataclasses import dataclass
from os.path import commonpath
from typing import TYPE_CHECKING, Final

from tox.util.path import ensure_private_dir

if TYPE_CHECKING:
    from pathlib import Path


PACKAGE_STAGING_DIR: Final[str] = "package"


def create_session_view(package: Path, temp_path: Path, trust_root: Path, work_dir: Path) -> Path:
    if temp_path.is_symlink():
        temp_path.unlink()
    repair_staging_path(temp_path, trust_root, work_dir)
    if sys.platform != "win32":
        _ensure_private_staging_path(temp_path, trust_root, os.geteuid())
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


def repair_staging_path(temp_path: Path, trust_root: Path, work_dir: Path) -> None:
    ensure_private_dir(temp_path)
    if sys.platform == "win32":  # pragma: win32 cover
        return
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
    user_id: Final[int] = os.geteuid()
    work_index: Final[int] = len(work_parts) - 1
    parts: Final[tuple[str, ...]] = (*work_parts, *staging_parts)
    directories: Final[list[_StagingDirectory]] = []
    with ExitStack() as stack:
        directory: int = os.open(trust_root.resolve(), flags)
        stack.callback(os.close, directory)
        for index, part in enumerate(parts):
            try:
                child = os.open(part, flags, dir_fd=directory)
            except OSError:
                return
            stack.callback(os.close, child)
            metadata: os.stat_result = os.fstat(child)
            if (
                metadata.st_uid != user_id
                or metadata.st_mode & stat.S_IWOTH
                or (index < work_index and metadata.st_mode & stat.S_IWGRP)
            ):
                return
            mode: int = stat.S_IMODE(metadata.st_mode)
            directories.append(
                _StagingDirectory(
                    parent_descriptor=directory,
                    name=part,
                    descriptor=child,
                    path=trust_root.joinpath(*parts[: index + 1]),
                    mode=mode,
                    # a fresh work dir is owner-only, which also hides group-writable environments left inside it
                    private_mode=mode & ~(0o077 if index == work_index else stat.S_IWGRP),
                )
            )
            directory = child

        for entry in directories:
            if entry.mode != entry.private_mode:
                os.fchmod(entry.descriptor, entry.private_mode)
        _verify_unchanged_staging_path(directories)


@dataclass(frozen=True, slots=True, kw_only=True)
class _StagingDirectory:
    parent_descriptor: int
    name: str
    descriptor: int
    path: Path
    mode: int
    private_mode: int


def _verify_unchanged_staging_path(directories: list[_StagingDirectory]) -> None:
    for entry in directories:
        msg: str = f"package staging path {entry.path} can be changed by another account"
        try:
            current: os.stat_result = os.stat(entry.name, dir_fd=entry.parent_descriptor, follow_symlinks=False)
        except OSError as exc:
            raise PermissionError(msg) from exc
        original: os.stat_result = os.fstat(entry.descriptor)
        if (current.st_dev, current.st_ino) != (original.st_dev, original.st_ino):
            raise PermissionError(msg)


def _ensure_private_staging_path(temp_path: Path, trust_root: Path, user_id: int) -> None:
    trusted_roots: Final[set[Path]] = {trust_root, trust_root.resolve()}
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
    "PACKAGE_STAGING_DIR",
    "create_session_view",
    "repair_staging_path",
]
