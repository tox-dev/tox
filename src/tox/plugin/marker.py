from __future__ import annotations

from typing import Final

import pluggy

NAME: Final[str] = "tox"  #: the name of the tox hook

impl: Final[pluggy.HookimplMarker] = pluggy.HookimplMarker(NAME)  #: decorator to mark tox plugin hooks


__all__ = [
    "NAME",
    "impl",
]
