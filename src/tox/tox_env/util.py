from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from tox.config.types import Command

if TYPE_CHECKING:
    from tox.config.sets import CoreConfigSet, EnvConfigSet


def add_change_dir_conf(config: EnvConfigSet, core: CoreConfigSet) -> None:
    def _post_process_change_dir(value: Path) -> Path:
        if not value.is_absolute():
            value = (core.get("tox_root", Path) / value).resolve()
        return value

    config.add_config(
        keys=["change_dir", "changedir"],
        of_type=Path,
        default=lambda conf, name: conf.core.get("tox_root", Path),  # ruff:ignore[unused-lambda-argument]
        desc="change to this working directory when executing the test command",
        post_process=_post_process_change_dir,
    )


def add_commands_conf(config: EnvConfigSet) -> None:
    config.add_config(
        keys=["commands"],
        of_type=list[Command],
        default=[],
        desc="the commands to be called for testing",
    )


def add_ignore_errors_conf(config: EnvConfigSet) -> None:
    config.add_config(
        keys=["ignore_errors"],
        of_type=bool,
        default=False,
        desc="when executing the commands keep going even if a sub-command exits with non-zero exit code",
    )


__all__ = [
    "add_change_dir_conf",
    "add_commands_conf",
    "add_ignore_errors_conf",
]
