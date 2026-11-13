"""On UNIX we use selectors to drain streams efficiently, following CPython's subprocess implementation."""

from __future__ import annotations

import contextlib  # pragma: win32 no cover
import errno  # pragma: win32 no cover
import os  # pragma: win32 no cover
import selectors  # pragma: win32 no cover
from typing import TYPE_CHECKING, Final

from tox.util.typing_compat import override

from .read_via_thread import ReadViaThread  # pragma: win32 no cover

if TYPE_CHECKING:
    from collections.abc import Callable


_TIMEOUT_FOR_INTERRUPT: Final[float] = 0.05  # pragma: win32 no cover
"""Seconds to wait for output before checking whether the reader should stop."""
_READ_CHUNK_SIZE: Final[int] = 32768  # pragma: win32 no cover
"""Maximum number of bytes read from a stream at once."""


class ReadViaThreadUnix(ReadViaThread):  # pragma: win32 no cover
    """Read a file descriptor in a thread on Unix, waiting for it with a selector.

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
        selector = selectors.DefaultSelector()
        try:
            selector.register(self.file_no, selectors.EVENT_READ)
        except (OSError, ValueError):  # pragma: no cover  # untested error path
            return

        try:
            self._read_until_eof(selector)
        finally:
            selector.close()

    def _read_until_eof(self, selector: selectors.DefaultSelector) -> None:
        while selector.get_map() and not self.stop.is_set():
            try:
                ready = selector.select(timeout=_TIMEOUT_FOR_INTERRUPT)
            except OSError as exception:
                if isinstance(exception, OSError) and exception.errno != errno.EINTR:
                    raise
                continue

            if not ready:
                continue

            for key, _ in ready:
                self._read_chunk(selector, key)

    def _read_chunk(self, selector: selectors.DefaultSelector, key: selectors.SelectorKey) -> None:
        try:
            data = os.read(key.fd, _READ_CHUNK_SIZE)
        except OSError as exception:
            if exception.errno == errno.EINTR:
                return
            if exception.errno not in {errno.EBADF, errno.EIO}:  # pragma: no cover  # setup not built by tests
                raise  # pragma: no cover  # untested error path
            data = b""

        if data:
            self.handler(data)
        else:
            self._safe_unregister(selector, key)

    @staticmethod
    def _safe_unregister(selector: selectors.DefaultSelector, key: selectors.SelectorKey) -> None:
        with contextlib.suppress(KeyError, ValueError):
            selector.unregister(key.fileobj)

    @override
    def _drain_stream(self) -> None:
        selector = selectors.DefaultSelector()
        try:
            selector.register(self.file_no, selectors.EVENT_READ)
        except (OSError, ValueError):  # pragma: no cover  # untested error path
            return

        with contextlib.closing(selector):
            while selector.get_map():
                try:
                    ready = selector.select(timeout=0)
                except OSError as exception:
                    # not reached in tests
                    if isinstance(exception, OSError) and exception.errno != errno.EINTR:  # pragma: no cover
                        raise  # pragma: no cover  # untested error path
                    continue

                if not ready:
                    break

                for key, _ in ready:
                    self._read_chunk(selector, key)


__all__ = [
    "ReadViaThreadUnix",
]
