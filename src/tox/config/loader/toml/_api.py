from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import TypeAlias

TomlTypes: TypeAlias = dict[str, "TomlTypes"] | list["TomlTypes"] | str | int | float | bool | None

__all__ = [
    "TomlTypes",
]
