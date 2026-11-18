from __future__ import annotations

__lazy_modules__ = [
    f"{__spec__.parent}.run",  # ty: ignore[missing-union-attribute]  # imported modules have a spec
    f"{__spec__.parent}.version",  # ty: ignore[missing-union-attribute]  # imported modules have a spec
]

from .run import main
from .version import version as __version__

__all__ = [
    "__version__",
    "main",
]
