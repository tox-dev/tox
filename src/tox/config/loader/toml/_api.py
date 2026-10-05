from __future__ import annotations

from typing import TYPE_CHECKING

from tox.config.set_env import SetEnvReference

if TYPE_CHECKING:
    from typing import TypeAlias

TomlTypes: TypeAlias = dict[str, "TomlTypes"] | list["TomlTypes"] | str | int | float | bool | SetEnvReference | None

__all__ = [
    "TomlTypes",
]
