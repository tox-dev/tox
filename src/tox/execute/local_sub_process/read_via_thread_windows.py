"""On Windows we use overlapped I/O with blocking wait for efficient real-time stream reading."""

from __future__ import annotations  # pragma: win32 cover

import _overlapped  # type: ignore[import-untyped]  # pragma: win32 cover # noqa: PLC2701
from typing import TYPE_CHECKING

from .read_via_thread import ReadViaThread  # pragma: win32 cover

if TYPE_CHECKING:
    from collections.abc import Callable

READ_CHUNK_SIZE = 32768  # pragma: win32 cover


class ReadViaThreadWindows(ReadViaThread):  # pragma: win32 cover
    def __init__(self, file_no: int, handler: Callable[[bytes], int], name: str, drain: bool) -> None:  # noqa: FBT001
        super().__init__(file_no, handler, name, drain)

    def _read_stream(self) -> None:
        try:
            while not self.stop.is_set():
                ov = _overlapped.Overlapped(0)
                try:
                    ov.ReadFile(self.file_no, READ_CHUNK_SIZE)
                except OSError:
                    break

                try:
                    data = ov.getresult(True)  # noqa: FBT003  # Blocking wait for I/O completion
                except OSError:
                    break

                if not data:
                    break
                self.handler(data)
        except OSError:  # pragma: no cover
            pass

    def _drain_stream(self) -> None:
        try:
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
        except OSError:  # pragma: no cover
            pass
