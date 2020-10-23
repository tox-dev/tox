"""
A reader that drain a stream via its file no on a background thread.
"""
from abc import ABC, abstractmethod
from threading import Event, Thread
from types import TracebackType
from typing import Callable, Optional, Type

WAIT_GENERAL = 0.1


class ReadViaThread(ABC):
    def __init__(self, file_no: int, handler: Callable[[bytes], None]) -> None:
        self.file_no = file_no
        self.stop = Event()
        self.thread = Thread(target=self._read_stream)
        self.handler = handler

    def __enter__(self) -> "ReadViaThread":
        self.thread.start()
        return self

    def __exit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
        thrown = None
        while True:
            try:
                self.stop.set()
                while self.thread.is_alive():
                    self.thread.join(WAIT_GENERAL)
            except KeyboardInterrupt as exception:  # pragma: no cover
                thrown = exception  # pragma: no cover
                continue  # pragma: no cover
            else:
                if thrown is not None:
                    raise thrown  # pragma: no cover
                else:  # pragma: no cover
                    break  # pragma: no cover
        if exc_val is None:  # drain what remains if we were not interrupted
            try:
                data = self._drain_stream()
            except ValueError:  # pragma: no cover
                pass  # pragma: no cover
            else:
                while True:
                    try:
                        self.handler(data)
                        break
                    except KeyboardInterrupt as exception:  # pragma: no cover
                        thrown = exception  # pragma: no cover
                if thrown is not None:
                    raise thrown  # pragma: no cover

    @abstractmethod
    def _read_stream(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def _drain_stream(self) -> bytes:
        raise NotImplementedError
