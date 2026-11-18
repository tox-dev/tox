from __future__ import annotations

__lazy_modules__ = ["typing"]

from typing import Final

import pluggy

NAME: Final[str] = "tox"  #: the name of the tox hook

#: decorator to mark tox plugin hooks
impl: Final[pluggy.HookimplMarker] = pluggy.HookimplMarker(NAME)  # simplint: ignore[module-variable-case]  # plugin API


__all__ = [
    "NAME",
    "impl",
]
