from __future__ import annotations

__lazy_modules__ = [f"{__spec__.parent}.api", f"{__spec__.parent}.discover"]  # ty: ignore[missing-union-attribute]  # imported modules have a spec

from .api import Source
from .discover import discover_source

__all__ = [
    "Source",
    "discover_source",
]
