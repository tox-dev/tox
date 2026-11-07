"""On Windows we use overlapped I/O for efficient real-time stream reading."""

from __future__ import annotations  # pragma: win32 cover

import contextlib  # pragma: win32 cover
import sys  # pragma: win32 cover
from typing import TYPE_CHECKING, Final, cast

from tox.util.typing_compat import override

if TYPE_CHECKING or sys.platform == "win32":  # pragma: win32 cover
    import _overlapped  # pragma: win32 cover # ruff:ignore[import-private-name]

import time  # pragma: win32 cover

from .read_via_thread import ReadViaThread  # pragma: win32 cover

if TYPE_CHECKING:
    from collections.abc import Callable

READ_CHUNK_SIZE: Final[int] = 32768  # pragma: win32 cover
"""Maximum number of bytes read from a pipe at once."""
POLL_INTERVAL: Final[float] = 0.05  # pragma: win32 cover
"""Seconds to wait between two checks of a pipe for new output."""
ERROR_IO_INCOMPLETE: Final[int] = 996  # pragma: win32 cover
"""Windows error code of a read that has not received any data yet."""


class ReadViaThreadWindows(ReadViaThread):  # pragma: win32 cover
    """Read a pipe in a thread on Windows, polling it for output.

    :param file_no: the file descriptor to read from
    :param handler: the callback that receives what is read
    :param name: the name of the stream, used to name the thread
    :param drain: whether to read the remaining content when the reader is exited
    """

    def __init__(  # keeps the signature
        self,
        file_no: int,
        handler: Callable[[bytes], int],
        name: str,
        drain: bool,  # ruff:ignore[boolean-type-hint-positional-argument]  # keeps the signature
    ) -> None:
        super().__init__(file_no, handler, name, drain)

    @override
    def _read_stream(self) -> None:
        with contextlib.suppress(OSError):  # pragma: no cover  # setup not built by tests
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
                    data = cast(  # mirrors signature
                        "bytes",
                        ov.getresult(False),  # ruff:ignore[boolean-positional-value-in-call]  # mirrors signature
                    )
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

    @override
    def _drain_stream(self) -> None:
        with contextlib.suppress(OSError):  # pragma: no cover  # setup not built by tests
            self._do_drain_stream()

    def _do_drain_stream(self) -> None:
        while True:
            ov = _overlapped.Overlapped(0)
            try:
                ov.ReadFile(self.file_no, READ_CHUNK_SIZE)
            except OSError:
                break

            try:
                data = cast(  # mirrors signature
                    "bytes",
                    ov.getresult(True),  # ruff:ignore[boolean-positional-value-in-call]  # mirrors signature
                )
            except OSError:
                break

            if not data:
                break
            self.handler(data)
