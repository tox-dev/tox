"""On Windows we use overlapped I/O for efficient real-time stream reading."""

from __future__ import annotations  # pragma: win32 cover

import contextlib  # pragma: win32 cover
import sys  # pragma: win32 cover

if sys.platform == "win32":  # pragma: win32 cover
    import _overlapped  # pragma: win32 cover # noqa: PLC2701

import time  # pragma: win32 cover
from typing import TYPE_CHECKING

from .read_via_thread import ReadViaThread  # pragma: win32 cover

if TYPE_CHECKING:
    from collections.abc import Callable

READ_CHUNK_SIZE = 32768  # pragma: win32 cover
POLL_INTERVAL = 0.05  # pragma: win32 cover
ERROR_IO_INCOMPLETE = 996  # pragma: win32 cover


class ReadViaThreadWindows(ReadViaThread):  # pragma: win32 cover
    def __init__(self, file_no: int, handler: Callable[[bytes], int], name: str, drain: bool) -> None:  # noqa: FBT001
        super().__init__(file_no, handler, name, drain)

    def _read_stream(self) -> None:
        with contextlib.suppress(OSError):  # pragma: no cover
            self._do_read_stream()

    def _do_read_stream(self) -> None:
        while not self.stop.is_set():
            ov = _overlapped.Overlapped(0)
            try:
                ov.ReadFile(self.file_no, READ_CHUNK_SIZE)
            except OSError:
                break

            while True:
                try:
                    data = ov.getresult(False)  # noqa: FBT003
                    break
                except OSError as exception:
                    if getattr(exception, "winerror", None) != ERROR_IO_INCOMPLETE:
                        return
                    if self.stop.is_set():  # stop requested while the read is still pending; abandon it
                        return
                    time.sleep(POLL_INTERVAL)

            if not data:
                break
            self.handler(data)

    def _drain_stream(self) -> None:
        with contextlib.suppress(OSError):  # pragma: no cover
            self._do_drain_stream()

    def _do_drain_stream(self) -> None:
        while True:
            ov = _overlapped.Overlapped(0)
            try:
                ov.ReadFile(self.file_no, READ_CHUNK_SIZE)
            except OSError:
                break

            try:
                data = ov.getresult(True)  # noqa: FBT003
            except OSError:
                break

            if not data:
                break
            self.handler(data)
