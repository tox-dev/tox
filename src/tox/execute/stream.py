from __future__ import annotations

from contextlib import contextmanager
from threading import Lock, Timer
from typing import IO, TYPE_CHECKING

from colorama import Fore

from tox.util.typing_compat import override

if TYPE_CHECKING:
    from collections.abc import Generator
    from types import TracebackType
    from typing import Self


class SyncWrite:
    """Make sure data collected is synced in-memory and to the target stream on every newline and time period.

    Used to propagate executed commands output to the standard output/error streams visible to the user.

    :param name: the name of the stream, used in the timer thread name
    :param target: the stream the content is synced to, or ``None`` to only collect it
    :param color: the color the content is shown in

    :var REFRESH_RATE: the seconds between two syncs to the target stream
    :var timer: the timer that syncs the content on the refresh period

    """

    REFRESH_RATE = 0.1

    def __init__(self, name: str, target: IO[bytes] | None, color: str | None = None) -> None:
        self._content = bytearray()
        self._target: IO[bytes] | None = target
        self._target_enabled: bool = target is not None
        self._content_lock: Lock = Lock()
        self._lock: Lock = Lock()
        self._at: int = 0
        self._color: str | None = color
        self.name = name

    @override
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, target={self._target!r}, color={self._color!r})"

    def __enter__(self) -> Self:
        if self._target_enabled:
            self._start()
        return self

    def _start(self) -> None:
        self.timer = Timer(self.REFRESH_RATE, self._trigger_timer)
        self.timer.name = f"{self.name}-sync-timer"
        self.timer.start()

    def _trigger_timer(self) -> None:
        with self._content_lock:
            at = len(self._content)
        self._write(at)

    def _write(self, at: int) -> None:
        assert self._target is not None  # because _do_print is guarding the call of this method  # ruff:ignore[assert]
        with self._lock:
            if at > self._at:  # pragma: no branch  # other outcome untested
                try:
                    with self.colored():
                        self._target.write(self._content[self._at : at])
                    self._target.flush()
                finally:
                    self._at = at

    @contextmanager
    def colored(self) -> Generator[None, None, None]:
        """Wrap the content written inside the block in the color of the stream, when a color is set.

        :yields: ``None``, the block runs with the color applied

        """
        if self._color is None or self._target is None:
            yield
        else:
            self._target.write(str(self._color).encode("utf-8"))
            try:
                yield
            finally:
                self._target.write(str(Fore.RESET).encode("utf-8"))

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._target_enabled:
            self.timer.cancel()
            self._write(len(self._content))

    @property
    def text(self) -> str:
        """The collected content decoded as UTF-8, keeping the bytes that are not valid UTF-8."""
        with self._content_lock:
            return self._content.decode("utf-8", errors="surrogateescape")

    @property
    def content(self) -> bytearray:
        """The collected content, as raw bytes."""
        with self._content_lock:
            return self._content

    def handler(self, content: bytes) -> int:
        """A callback called whenever content is written.

        :param content: the bytes that were written

        :returns: the number of bytes handled

        """
        with self._content_lock:
            self._content.extend(content)
            if self._target_enabled is False:
                return len(content)
            at = content.rfind(b"\n")
            if at != -1:  # pragma: no branch  # other outcome untested
                at = len(self._content) - len(content) + at + 1
        self.timer.cancel()
        try:
            if at != -1:
                self._write(at)
        finally:
            self._start()
        return len(content)


__all__ = [
    "SyncWrite",
]
