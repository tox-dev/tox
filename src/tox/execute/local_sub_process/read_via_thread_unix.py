"""On UNIX we use selectors to drain streams efficiently, following CPython's subprocess implementation."""

from __future__ import annotations

import contextlib  # pragma: win32 no cover
import errno  # pragma: win32 no cover
import os  # pragma: win32 no cover
import selectors  # pragma: win32 no cover
from typing import TYPE_CHECKING, Any

from .read_via_thread import ReadViaThread  # pragma: win32 no cover

if TYPE_CHECKING:
    from collections.abc import Callable

TIMEOUT_FOR_INTERRUPT = 0.05  # pragma: win32 no cover
READ_CHUNK_SIZE = 32768  # pragma: win32 no cover


class ReadViaThreadUnix(ReadViaThread):  # pragma: win32 no cover
    def __init__(self, file_no: int, handler: Callable[[bytes], int], name: str, drain: bool) -> None:  # noqa: FBT001
        super().__init__(file_no, handler, name, drain)

    def _read_stream(self) -> None:
        selector = selectors.DefaultSelector()
        try:
            selector.register(self.file_no, selectors.EVENT_READ)
        except (OSError, ValueError):  # pragma: no cover
            return

        try:
            self._read_until_eof(selector)
        finally:
            selector.close()

    def _read_until_eof(self, selector: selectors.DefaultSelector) -> None:
        while selector.get_map() and not self.stop.is_set():
            try:
                ready = selector.select(timeout=TIMEOUT_FOR_INTERRUPT)
            except (InterruptedError, OSError) as exception:
                if isinstance(exception, OSError) and exception.errno != errno.EINTR:
                    raise
                continue

            if not ready:
                continue

            for key, _ in ready:
                self._read_chunk(selector, key)

    def _drain_stream(self) -> None:
        selector = selectors.DefaultSelector()
        try:
            selector.register(self.file_no, selectors.EVENT_READ)
        except (OSError, ValueError):  # pragma: no cover
            return

        try:
            while selector.get_map():
                try:
                    ready = selector.select(timeout=0)
                except (InterruptedError, OSError) as exception:
                    if isinstance(exception, OSError) and exception.errno != errno.EINTR:  # pragma: no cover
                        raise  # pragma: no cover
                    continue

                if not ready:
                    break

                for key, _ in ready:
                    self._read_chunk(selector, key)
        finally:
            selector.close()

    def _read_chunk(self, selector: selectors.DefaultSelector, key: selectors.SelectorKey) -> None:
        try:
            data = os.read(key.fd, READ_CHUNK_SIZE)
        except OSError as exception:
            if exception.errno == errno.EINTR:
                return
            if exception.errno not in {errno.EBADF, errno.EIO}:  # pragma: no cover
                raise  # pragma: no cover
            data = b""

        if data:
            self.handler(data)
        else:
            self._safe_unregister(selector, key.fileobj)

    @staticmethod
    def _safe_unregister(selector: selectors.DefaultSelector, fileobj: Any) -> None:
        with contextlib.suppress(KeyError, ValueError):
            selector.unregister(fileobj)
