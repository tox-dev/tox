"""A reader that drains a stream via its file descriptor, following CPython's subprocess approach."""

from __future__ import annotations

from abc import ABC, abstractmethod
from threading import Event, Thread
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import TracebackType
    from typing import Self


WAIT_GENERAL: Final[float] = 0.05


class ReadViaThread(ABC):
    def __init__(  # keeps the signature
        self,
        file_no: int,
        handler: Callable[[bytes], int],
        name: str,
        drain: bool,  # ruff:ignore[boolean-type-hint-positional-argument]  # keeps the signature
    ) -> None:
        self.file_no = file_no
        self.stop = Event()
        self.thread = Thread(target=self._read_stream, name=f"tox-r-{name}-{file_no}")
        self.handler = handler
        self._on_exit_drain = drain

    @abstractmethod
    def _read_stream(self) -> None:
        raise NotImplementedError

    def __enter__(self) -> Self:
        self.thread.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.stop.set()
        while self.thread.is_alive():
            self.thread.join(WAIT_GENERAL)
        if self._on_exit_drain:
            self._drain_stream()

    @abstractmethod
    def _drain_stream(self) -> None:
        raise NotImplementedError
