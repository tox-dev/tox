"""Point the project's :PEP:`832` ``.venv`` redirect file at a tox environment."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)
_FILE_NAME: Final[str] = ".venv"


def record_venv_redirect(root: Path, env: Path, is_ours: Callable[[Path], bool]) -> None:
    """Point the :PEP:`832` ``.venv`` redirect file under *root* at *env*.

    Leaves a ``.venv`` directory or symlink alone, and a redirect file pointing where *is_ours* rejects, since then the
    user or another tool picked the environment.

    :param root: the directory holding the redirect file, the project root
    :param env: the environment directory to point at
    :param is_ours: tells whether an existing redirect target belongs to tox, and so may be replaced

    """
    file = root / _FILE_NAME
    if (file.exists() or file.is_symlink()) and (
        (target := _redirect_target(file)) is None or target == env or not is_ours(target)
    ):
        return
    line = env.relative_to(root).as_posix() if env.is_relative_to(root) else str(env)
    try:
        file.write_text(f"{line}\n", encoding="utf-8")
    except OSError as exc:
        _LOGGER.warning("could not point %s at %s: %s", file, env, exc)


def forget_venv_redirect(root: Path, env: Path) -> None:
    """Remove the :PEP:`832` ``.venv`` redirect file under *root* when it points at *env*.

    Call this when the environment stops being usable, such as while tox recreates it, so that nothing points a reader
    at a half-built environment. The PEP rules an empty redirect file invalid, so removal is the only retraction.

    :param root: the directory holding the redirect file, the project root
    :param env: the environment directory being retracted

    """
    if _redirect_target(file := root / _FILE_NAME) == env:
        file.unlink()


def _redirect_target(file: Path) -> Path | None:
    if file.is_symlink() or not file.is_file():
        return None
    try:
        text = file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):  # not a redirect file tox can read, so not one tox wrote
        return None
    line = text.removesuffix("\n")  # universal newlines already turned \r\n into \n
    return Path(os.path.normpath(file.parent / line))


__all__ = [
    "forget_venv_redirect",
    "record_venv_redirect",
]
