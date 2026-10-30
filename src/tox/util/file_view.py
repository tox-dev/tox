from __future__ import annotations

import logging
import os
import shutil
import stat
import sys
from os.path import commonpath
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from pathlib import Path


def create_session_view(package: Path, temp_path: Path, trust_root: Path | None = None) -> Path:
    if temp_path.is_symlink():
        temp_path.unlink()
    temp_path.mkdir(parents=True, exist_ok=True)
    if sys.platform != "win32":
        _ensure_private_staging_path(temp_path, trust_root, os.geteuid())
    file_id: Final[int] = max((int(entry.name) for entry in temp_path.iterdir() if entry.name.isnumeric()), default=0)
    session_dir: Final[Path] = temp_path / str(file_id + 1)
    session_dir.mkdir()
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


__all__ = ["create_session_view"]
