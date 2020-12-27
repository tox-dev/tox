"""
On Windows we use overlapped mechanism, borrowing it from asyncio (but without the event loop).
"""
import logging
from asyncio.windows_utils import BUFSIZE  # pragma: win32 cover
from time import sleep
from typing import Callable, Optional  # pragma: win32 cover

import _overlapped  # type: ignore[import]  # pragma: win32 cover

from .read_via_thread import ReadViaThread  # pragma: win32 cover


class ReadViaThreadWindows(ReadViaThread):  # pragma: win32 cover
    def __init__(self, file_no: int, handler: Callable[[bytes], None], name: str, drain: bool) -> None:
        super().__init__(file_no, handler, name, drain)
        self.closed = False
        self._ov = _overlapped.Overlapped(0)
        self._read = False

    def _read_stream(self) -> None:
        keep_reading = True
        while keep_reading:  # try to read at least once
            wait = self._read_batch()
            if wait is None:
                break
            if wait is True:
                sleep(0.01)  # sleep for 10ms if there was no data to read and try again
            keep_reading = not self.stop.is_set()

    def _drain_stream(self) -> None:
        wait: Optional[bool] = False
        while wait is not True:
            wait = self._read_batch()

    def _read_batch(self) -> Optional[bool]:
        if self._read is False:
            try:  # read up to BUFSIZE at a time
                self._ov.ReadFile(self.file_no, BUFSIZE)  # type: ignore[attr-defined]
                self._read = True
            except BrokenPipeError:
                self.closed = True
                return None
        try:  # wait=False to not block and give chance for the stop check
            data = self._ov.getresult(False)
        except OSError as exception:
            # 996 0 (0x3E4) - Overlapped I/O event is not in a signaled state
            if getattr(exception, "winerror", None) == 996:
                return True
            else:
                logging.error("failed to read %r", exception)
                return None
        else:
            self._read = False
            self.handler(data)
        return False
