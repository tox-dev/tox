"""On Windows we use overlapped mechanism, borrowing it from asyncio (but without the event loop)."""

from __future__ import annotations  # pragma: win32 cover

import _overlapped  # pragma: win32 cover # noqa: PLC2701  # ty: ignore[unresolved-import] # no typeshed stubs
import logging  # pragma: win32 cover
from asyncio.windows_utils import (
    BUFSIZE,
)  # pragma: win32 cover
from time import sleep  # pragma: win32 cover
from typing import TYPE_CHECKING

from .read_via_thread import ReadViaThread  # pragma: win32 cover

if TYPE_CHECKING:
    from collections.abc import Callable


class ReadViaThreadWindows(ReadViaThread):  # pragma: win32 cover
    def __init__(self, file_no: int, handler: Callable[[bytes], int], name: str, drain: bool) -> None:  # noqa: FBT001
        super().__init__(file_no, handler, name, drain)
        self.closed = False
        self._ov: _overlapped.Overlapped | None = None
        self._waiting_for_read = False

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
        wait: bool | None = self.closed
        while wait is False:
            wait = self._read_batch()

    def _read_batch(self) -> bool | None:
        """:returns: None means error can no longer read, True wait for result, False try again"""
        if self._waiting_for_read is False:
            self._ov = _overlapped.Overlapped(0)  # can use it only once to read a batch
            try:  # read up to BUFSIZE at a time
                self._ov.ReadFile(self.file_no, BUFSIZE)
                self._waiting_for_read = True
            except OSError:
                self.closed = True
                return None
        try:  # wait=False to not block and give chance for the stop check
            data = self._ov.getresult(False)  # noqa: FBT003  # ty: ignore[unresolved-attribute] # https://github.com/astral-sh/ty/issues/160
        except OSError as exception:
            # 996 (0x3E4) Overlapped I/O event is not in a signaled state.
            # 995 (0x3E3) The I/O operation has been aborted because of either a thread exit or an application request.
            win_error = getattr(exception, "winerror", None)
            if win_error == 996:  # noqa: PLR2004
                return True
            if win_error != 995:  # noqa: PLR2004
                logging.error("failed to read %r", exception)  # noqa: TRY400
            return None
        else:
            self._ov = None
            self._waiting_for_read = False
            if data:
                self.handler(data)
            else:
                return None
        return False
