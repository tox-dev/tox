from __future__ import annotations

import json
import logging
import os
import shutil
import stat
import sys
from contextlib import ExitStack, suppress
from dataclasses import dataclass
from os.path import commonpath
from pathlib import Path
from typing import Final

from .path import ensure_empty_dir, ensure_private_dir

PACKAGE_STAGING_DIR: Final[str] = "package"
"""Name of the directory that holds the staged copy of the package."""


def create_session_view(package: Path, temp_path: Path, trust_root: Path) -> Path:
    """Create the view of the package that a session installs from, which lives in the temporary path.

    :param package: the package to view
    :param temp_path: the temporary directory the view is created in
    :param trust_root: the directory the view is restricted to

    :returns: the path of the view
    """
    if temp_path.is_symlink():
        temp_path.unlink()
    ensure_private_dir(temp_path)
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


def _ensure_private_staging_path(temp_path: Path, trust_root: Path, user_id: int) -> None:
    trusted_roots: Final[set[Path]] = {trust_root, trust_root.resolve()}
    project: Final[os.stat_result] = trust_root.resolve().stat()
    owners: Final[frozenset[int]] = frozenset({0, user_id, project.st_uid})
    for candidate in {temp_path, temp_path.resolve()}:
        for parent in (candidate, *candidate.parents):
            if parent in trusted_roots:
                break
            metadata: os.stat_result = parent.stat()
            mutable_link: bool = (
                parent.is_symlink()
                and bool(parent.parent.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH))
                and parent.lstat().st_uid not in owners
            )
            if mutable_link or _exceeds_project_writers(metadata, project, owners):
                mode: int = stat.S_IMODE(metadata.st_mode)
                msg: str = (
                    f"package staging path {parent} (owner uid {metadata.st_uid}, mode {mode:04o}) "
                    f"can be changed by an account that cannot change {trust_root}"
                )
                raise PermissionError(msg)


def _exceeds_project_writers(metadata: os.stat_result, project: os.stat_result, owners: frozenset[int]) -> bool:
    if metadata.st_uid not in owners:
        return True
    if metadata.st_mode & stat.S_ISVTX:
        return False
    project_sticky: Final[bool] = bool(project.st_mode & stat.S_ISVTX)
    project_world_writable: Final[bool] = bool(project.st_mode & stat.S_IWOTH) and not project_sticky
    project_group_writable: Final[bool] = bool(project.st_mode & stat.S_IWGRP) and not project_sticky
    if metadata.st_mode & stat.S_IWOTH and not project_world_writable:
        return True
    return bool(metadata.st_mode & stat.S_IWGRP) and not (
        project_world_writable or (project_group_writable and metadata.st_gid == project.st_gid)
    )


def repair_staging_path(temp_path: Path, trust_root: Path, work_dir: Path) -> None:
    """Repair the staging path of a session view, when it was replaced by a link.

    :param temp_path: the staging path
    :param trust_root: the directory the view is restricted to
    :param work_dir: the working directory of the run
    """
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
    project: Final[os.stat_result] = trust_root.resolve().stat()
    owners: Final[frozenset[int]] = frozenset({0, os.geteuid(), project.st_uid})
    work_index: Final[int] = len(work_parts) - 1
    with ExitStack() as stack:
        directories: Final = _open_staging_chain(stack, trust_root, (*work_parts, *staging_parts), flags)
        if directories is None:
            return
        exposed: Final = _exposed_index(directories, work_index, project, owners)
        if exposed is None:
            return
        _lock_exposed_directories(directories, exposed, work_index)
        _empty_exposed_directory(directories[exposed].path, owners, trust_root)


def _open_staging_chain(
    stack: ExitStack, trust_root: Path, parts: tuple[str, ...], flags: int
) -> list[_StagingDirectory] | None:
    # the chain stops at the first missing component; any other failure (a symlink, a file) leaves it unrepaired
    directories: Final[list[_StagingDirectory]] = []
    directory: int = os.open(trust_root.resolve(), flags)
    stack.callback(os.close, directory)
    for index, part in enumerate(parts):
        try:
            child = os.open(part, flags, dir_fd=directory)
        except FileNotFoundError:
            break
        except OSError:
            return None
        stack.callback(os.close, child)
        directories.append(
            _StagingDirectory(
                parent_descriptor=directory,
                name=part,
                descriptor=child,
                path=trust_root.joinpath(*parts[: index + 1]),
                metadata=os.fstat(child),
            )
        )
        directory = child
    return directories


@dataclass(frozen=True, slots=True, kw_only=True)
class _StagingDirectory:
    parent_descriptor: int
    name: str
    descriptor: int
    path: Path
    metadata: os.stat_result


def _exposed_index(
    directories: list[_StagingDirectory], work_index: int, project: os.stat_result, owners: frozenset[int]
) -> int | None:
    # the outermost directory the project's writers do not control is locked together with everything below it
    first: Final[int] = max(work_index, 0)
    # between the project and the work dir tox must not change user directories; the check reports them later
    if any(_exceeds_project_writers(entry.metadata, project, owners) for entry in directories[:first]):
        return None
    if any(entry.metadata.st_uid not in owners for entry in directories[first:]):
        return None
    return next(
        (
            index
            for index in range(first, len(directories))
            if _exceeds_project_writers(directories[index].metadata, project, owners)
        ),
        None,
    )


def _lock_exposed_directories(directories: list[_StagingDirectory], exposed: int, work_index: int) -> None:
    for index, entry in enumerate(directories[exposed:], start=exposed):
        mode: int = stat.S_IMODE(entry.metadata.st_mode)
        # a fresh work dir is owner-only, which also hides group-writable environments left inside it
        private_mode: int = mode & ~0o077 if index == work_index else mode & ~(stat.S_IWGRP | stat.S_IWOTH)
        os.fchmod(entry.descriptor, private_mode)
    _verify_unchanged_staging_path(directories)


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


def _empty_exposed_directory(path: Path, owners: frozenset[int], trust_root: Path) -> None:
    for directory, dirnames, filenames in os.walk(path, followlinks=False):
        for name in (*dirnames, *filenames):
            entry: Path = Path(directory, name)
            uid: int = os.lstat(entry).st_uid
            if uid not in owners:
                msg = f"{entry} is owned by uid {uid}, which cannot change {trust_root}; tox will not remove it"
                raise PermissionError(msg)
    kept: Final[str | None] = _kept_entry(path)
    ensure_empty_dir(path, except_filename=kept)
    if kept is not None and not (path / kept).is_symlink():
        # the kept environment may have been changed while exposed, so its setup must not be reused
        _mark_stale(path / kept)
    logging.warning(
        "%s could be changed by accounts that cannot change %s; made it private and removed its contents so tox"
        " recreates them",
        path,
        trust_root,
    )


def _kept_entry(directory: Path) -> str | None:
    # the running environment may live in the work dir; keep it so the provisioned tox can finish
    try:
        relative: Final[Path] = Path(sys.prefix).resolve().relative_to(directory.resolve())
    except ValueError:
        return None
    return relative.parts[0] if relative.parts else None


def _mark_stale(environment: Path) -> None:
    info: Final[Path] = environment / ".tox-info.json"
    with suppress(FileNotFoundError):
        info.unlink()  # a planted link is removed itself, never followed
    # O_EXCL fails on any existing entry, a new link included; an empty Python section never equals the
    # configuration, so the next setup recreates the environment
    descriptor: Final[int] = os.open(info, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handler:
        handler.write(json.dumps({"Python": {}}))


__all__ = [
    "PACKAGE_STAGING_DIR",
    "create_session_view",
    "repair_staging_path",
]
