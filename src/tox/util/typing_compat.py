"""Typing names that moved into the standard library after the oldest Python tox supports."""

from __future__ import annotations

import sys

if sys.version_info >= (3, 12):  # pragma: >=3.12 cover
    from typing import override
else:  # pragma: <3.12 cover
    from typing_extensions import override

__all__ = [
    "override",
]
