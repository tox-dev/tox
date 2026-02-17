"""A reader that drains a stream via its file descriptor, following CPython's subprocess approach."""

from __future__ import annotations

from abc import ABC, abstractmethod
from threading import Event, Thread
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sys
    from collections.abc import Callable
    from types import TracebackType

    if sys.version_info >= (3, 11):  # pragma: no cover (py311+)
        from typing import Self
    else:  # pragma: no cover (<py311)
        from typing_extensions import Self


WAIT_GENERAL = 0.05


class ReadViaThread(ABC):
    def __init__(self, file_no: int, handler: Callable[[bytes], int], name: str, drain: bool) -> None:  # noqa: FBT001
        self.file_no = file_no
        self.stop = Event()
        self.thread = Thread(target=self._read_stream, name=f"tox-r-{name}-{file_no}")
        self.handler = handler
        self._on_exit_drain = drain

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
    def _read_stream(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def _drain_stream(self) -> None:
        raise NotImplementedError
