"""Catalog the project environments in a :PEP:`832` ``.python-envs`` file."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from filelock import FileLock

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

_FILE_NAME: Final[str] = ".python-envs"
_LOCK_NAME: Final[str] = ".python-envs.lock"
_VENV_NAME: Final[str] = ".venv"


def record_python_envs(root: Path, work_dir: Path, envs: Sequence[Path]) -> None:
    """Write the :PEP:`832` ``.python-envs`` catalog of the tox environments.

    Writes the entries in the given order, so the caller decides the default environment by putting it last. Lines
    pointing outside *work_dir* come from another tool, so they stay as they are, and one of them sitting last keeps
    that spot. Skips a ``.venv`` under *root*, :PEP:`832` already treats it as the implicit final entry.

    :param root: the directory holding the file, the project root
    :param work_dir: the directory tox owns, *envs* replaces the lines under it
    :param envs: the environment directories to catalog, least preferred first

    """
    keep = [e for e in envs if e != root / _VENV_NAME]
    ours = set(keep)
    _rewrite(root, work_dir, lambda path: path in ours or path.is_relative_to(work_dir), keep)


def forget_python_env(root: Path, work_dir: Path, env: Path) -> None:
    """Drop an environment from the :PEP:`832` ``.python-envs`` catalog.

    Call this when the environment stops being usable, such as while tox recreates it, so that nothing points a reader
    at a half-built environment.

    :param root: the directory holding the file, the project root
    :param work_dir: the directory tox owns, hosts the lock guarding the file
    :param env: the environment directory to drop

    """
    _rewrite(root, work_dir, lambda path: path == env, [])


def _rewrite(root: Path, work_dir: Path, is_ours: Callable[[Path], bool], envs: Sequence[Path]) -> None:
    file = root / _FILE_NAME
    if not (envs or file.exists()):
        return
    work_dir.mkdir(parents=True, exist_ok=True)
    with FileLock(work_dir / _LOCK_NAME):
        current = file.read_text(encoding="utf-8") if file.exists() else None
        lines = [line for raw in (current or "").split("\n") if (line := raw.rstrip("\r"))]
        kept = [line for line in lines if not is_ours(root / line)]
        tail = [kept.pop()] if kept and lines[-1] == kept[-1] else []
        content = "".join(f"{line}\n" for line in [*kept, *(_as_line(e, root) for e in envs), *tail])
        if content != current:  # rewriting identical content would churn the file for no gain
            file.write_text(content, encoding="utf-8")


def _as_line(path: Path, root: Path) -> str:
    return str(path.relative_to(root) if path.is_relative_to(root) else path)


__all__ = [
    "forget_python_env",
    "record_python_envs",
]
