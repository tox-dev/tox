from typing import Any, Callable, TypeVar

import pluggy

from . import NAME

F = TypeVar("F", bound=Callable[..., Any])
impl: Callable[[F], F] = pluggy.HookimplMarker(NAME)
