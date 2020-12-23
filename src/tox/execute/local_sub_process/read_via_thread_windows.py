"""
On Windows we use overlapped mechanism, borrowing it from asyncio (but without the event loop).
"""
from asyncio.windows_utils import BUFSIZE  # pragma: win32 cover
from time import sleep
from typing import Callable  # pragma: win32 cover

import _overlapped  # type: ignore[import]  # pragma: win32 cover

from .read_via_thread import ReadViaThread  # pragma: win32 cover


class ReadViaThreadWindows(ReadViaThread):  # pragma: win32 cover
    def __init__(self, file_no: int, handler: Callable[[bytes], None], name: str, on_exit_drain: bool) -> None:
        super().__init__(file_no, handler, name, on_exit_drain)
        self.closed = False

    def _read_stream(self) -> None:
        ov = None
        keep_reading = True
        while keep_reading:
            if ov is None:  # if we have no overlapped handler create one
                ov = _overlapped.Overlapped(0)
                try:
                    # read up to BUFSIZE at a time
                    ov.ReadFile(self.file_no, BUFSIZE)  # type: ignore[attr-defined]
                except BrokenPipeError:
                    self.closed = True
                    return
            # this loop break condition is here to ensure we always try to drain a constructed overlap handler, either
            # after a period of sleep or after just constructing one
            keep_reading = not self.stop.is_set()
            try:
                data = ov.getresult(False)  # wait=False to not block and give chance for the stop check
            except OSError as exception:
                # 996 0 (0x3E4) - Overlapped I/O event is not in a signaled state
                if getattr(exception, "winerror", None) == 996:
                    sleep(0.01)  # sleep for 10ms if there was no data to read and try again
                    continue
                raise
            else:
                ov = None  # reset overlapped IO if the operation was a success
                self.handler(data)

    def _drain_stream(self) -> bytes:
        length, result = 1, b""
        while length:
            ov = _overlapped.Overlapped(0)
            try:
                ov.ReadFile(self.file_no, BUFSIZE)  # type: ignore[attr-defined]
                data = ov.getresult(False)
            except OSError:
                length = 0
            else:
                result += data
                length = len(data)
        return result
