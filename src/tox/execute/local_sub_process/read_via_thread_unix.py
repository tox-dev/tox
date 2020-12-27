"""
On UNIX we use select.select to ensure we drain in a non-blocking fashion.
"""
import errno  # pragma: win32 no cover
import os  # pragma: win32 no cover
import select  # pragma: win32 no cover
from typing import Callable  # pragma: win32 no cover

from .read_via_thread import ReadViaThread  # pragma: win32 no cover

STOP_EVENT_CHECK_PERIODICITY_IN_MS = 0.01  # pragma: win32 no cover


class ReadViaThreadUnix(ReadViaThread):  # pragma: win32 no cover
    def __init__(self, file_no: int, handler: Callable[[bytes], None], name: str, drain: bool) -> None:
        super().__init__(file_no, handler, name, drain)

    def _read_stream(self) -> None:
        while not self.stop.is_set():
            # we need to drain the stream, but periodically give chance for the thread to break if the stop event has
            # been set (this is so that an interrupt can be handled)
            if self._read_available() is False:
                break

    def _drain_stream(self) -> None:
        self._read_available(timeout=0.0001)

    def _read_available(self, timeout: float = STOP_EVENT_CHECK_PERIODICITY_IN_MS) -> bool:
        try:
            ready, __, ___ = select.select([self.file_no], [], [], timeout)
            if ready:
                data = os.read(self.file_no, ready[0])
                self.handler(data)
        except OSError as exception:
            if exception.errno == errno.EBADF:
                return False
            raise
        return True
