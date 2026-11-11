"""A reader that drains a stream via its file descriptor, following CPython's subprocess approach."""

from __future__ import annotations

from abc import ABC, abstractmethod
from threading import Event, Thread
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import TracebackType
    from typing import Self


_WAIT_GENERAL: Final[float] = 0.05  # simplint: ignore[single-user-constant]  # shutdown poll interval
"""Seconds to wait for a reader thread to finish before checking again."""


class ReadViaThread(ABC):
    """Read a file descriptor in a thread, and pass what is read to a handler.

    :param file_no: the file descriptor to read from
    :param handler: the callback that receives what is read
    :param name: the name of the stream, used to name the thread
    :param drain: whether to read the remaining content when the reader is exited

    :var stop: the event that asks the reader thread to stop
    :var thread: the thread that reads the file descriptor

    """

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
            self.thread.join(_WAIT_GENERAL)
        if self._on_exit_drain:
            self._drain_stream()

    @abstractmethod
    def _drain_stream(self) -> None:
        raise NotImplementedError


__all__ = [
    "ReadViaThread",
]
