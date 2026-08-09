from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TypeAlias

JsonValue: TypeAlias = bool | int | float | str | Sequence["JsonValue"] | Mapping[str, "JsonValue"] | None
"""A value that can round-trip through :mod:`json`, used for documents tox persists (journal, env cache)."""

__all__ = [
    "JsonValue",
]
