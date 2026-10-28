from __future__ import annotations

from typing import TYPE_CHECKING

from tox.config.loader.replacer import MatchExpression
from tox.config.set_env import SetEnvReference

if TYPE_CHECKING:
    from typing import TypeAlias

TomlTypes: TypeAlias = (
    dict[str, "TomlTypes"] | list["TomlTypes"] | str | int | float | bool | SetEnvReference | MatchExpression | None
)

__all__ = [
    "TomlTypes",
]
