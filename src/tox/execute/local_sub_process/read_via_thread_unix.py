"""
On UNIX we use select.select to ensure we drain in a non-blocking fashion.
"""
import os  # pragma: win32 no cover
import select  # pragma: win32 no cover
from typing import Callable  # pragma: win32 no cover

from .read_via_thread import ReadViaThread  # pragma: win32 no cover

STOP_EVENT_CHECK_PERIODICITY_IN_MS = 0.01  # pragma: win32 no cover


class ReadViaThreadUnix(ReadViaThread):  # pragma: win32 no cover
    def __init__(self, file_no: int, handler: Callable[[bytes], None]) -> None:
        super().__init__(file_no, handler)

    def _read_stream(self) -> None:
        while not self.stop.is_set():
            # we need to drain the stream, but periodically give chance for the thread to break if the stop event has
            # been set (this is so that an interrupt can be handled)
            ready, __, ___ = select.select([self.file_no], [], [], STOP_EVENT_CHECK_PERIODICITY_IN_MS)
            if ready:
                data = os.read(self.file_no, 1)
                if data:
                    self.handler(data)

    def _drain_stream(self) -> bytes:
        result = bytearray()  # on closed file read returns empty
        while True:
            try:
                last_result = os.read(self.file_no, 1)
            except OSError:  # ignore failing to read the pipe - already closed
                break
            if last_result:
                result.append(last_result[0])
            else:
                break
        return bytes(result)
