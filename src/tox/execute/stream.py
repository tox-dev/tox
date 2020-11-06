from contextlib import contextmanager
from threading import Event, Lock, Timer
from types import TracebackType
from typing import IO, Iterator, Optional, Type

from colorama import Fore


class CollectWrite:
    """A stream collector that is both time triggered and newline"""

    REFRESH_RATE = 0.1

    def __init__(self, target: Optional[IO[bytes]], color: Optional[str] = None) -> None:
        self._content = bytearray()
        self._print_to: Optional[IO[bytes]] = None if target is None else target
        self._do_print: bool = target is not None
        self._keep_printing: Event = Event()
        self._content_lock: Lock = Lock()
        self._print_lock: Lock = Lock()
        self._at: int = 0
        self._color: Optional[str] = color

    def __enter__(self) -> "CollectWrite":
        if self._do_print:
            self._start()
        return self

    def __exit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
        if self._do_print:
            self._cancel()
            self._print(len(self._content))

    def _start(self) -> None:
        self.timer = Timer(self.REFRESH_RATE, self._trigger_timer)
        self.timer.start()

    def _cancel(self) -> None:
        self.timer.cancel()

    def collect(self, content: bytes) -> None:
        with self._content_lock:
            self._content.extend(content)
            if self._do_print is False:
                return
            at = content.rfind(b"\n")
            if at != -1:
                at = len(self._content) - len(content) + at + 1
        if at != -1:
            self._cancel()
            try:
                self._print(at)
            finally:
                self._start()

    def _trigger_timer(self) -> None:
        with self._content_lock:
            at = len(self._content)
        self._print(at)

    def _print(self, at: int) -> None:
        assert self._print_to is not None  # because _do_print is guarding the call of this method
        with self._print_lock:
            if at > self._at:
                try:
                    with self.colored():
                        self._print_to.write(self._content[self._at : at])
                    self._print_to.flush()
                finally:
                    self._at = at

    @contextmanager
    def colored(self) -> Iterator[None]:
        if self._color is None or self._print_to is None:
            yield
        else:
            self._print_to.write(self._color.encode("utf-8"))
            try:
                yield
            finally:
                self._print_to.write(Fore.RESET.encode("utf-8"))

    @property
    def text(self) -> str:
        with self._content_lock:
            return self._content.decode("utf-8")
