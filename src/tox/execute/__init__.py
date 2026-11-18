"""Package that handles execution of commands within tox environments."""

from __future__ import annotations

__lazy_modules__ = [
    f"{__spec__.parent}.api",  # ty: ignore[missing-union-attribute]  # imported modules have a spec
    f"{__spec__.parent}.request",  # ty: ignore[missing-union-attribute]  # imported modules have a spec
]

from .api import Outcome
from .request import ExecuteRequest

__all__ = [
    "ExecuteRequest",
    "Outcome",
]
