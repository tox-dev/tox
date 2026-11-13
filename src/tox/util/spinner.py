"""A minimal non-colored version of https://pypi.org/project/halo, to track list progress."""

from __future__ import annotations

import os
import sys
import textwrap
import threading
import time
from collections import OrderedDict
from typing import IO, TYPE_CHECKING, Final, NamedTuple, Self, TypeVar

from colorama import Fore

if TYPE_CHECKING:
    from collections.abc import Sequence
    from types import TracebackType
    from typing import ClassVar

if sys.platform == "win32":  # pragma: win32 cover
    import ctypes

    class _CursorInfo(ctypes.Structure):
        _fields_ = [("size", ctypes.c_int), ("visible", ctypes.c_byte)]


def _file_support_encoding(chars: Sequence[str], file: IO[str]) -> bool:
    if (
        encoding := getattr(file, "encoding", None)
    ) is not None:  # pragma: no branch  # this should be always set, unless someone passes in something bad
        try:
            for char in chars:
                char.encode(encoding)
        except UnicodeEncodeError:
            pass
        else:
            return True
    return False


T = TypeVar("T", bound="Spinner")
"""Type variable bound to the spinner class, for methods that return the spinner."""
MISS_DURATION: Final[float] = 0.01
"""Seconds an environment must run for its duration to be shown."""


class _Outcome(NamedTuple):
    ok: str
    fail: str
    skip: str


class Spinner:
    """A spinner that shows the progress of the environments on a stream.

    :param enabled: whether the spinner is shown
    :param refresh_rate: the seconds between two frames
    :param colored: whether the outcome symbols are colored
    :param stream: the stream the spinner is written to, the standard output when ``None``
    :param total: the number of environments that are expected to run, ``None`` when unknown

    :var CLEAR_LINE: escape sequence that clears the line
    :var max_width: maximum width of an environment's text
    :var UNICODE_FRAMES: frames for streams that support Unicode
    :var ASCII_FRAMES: frames for streams that do not
    :var UNICODE_OUTCOME: outcome symbols for streams that support Unicode
    :var ASCII_OUTCOME: outcome symbols for streams that do not
    :var is_colored: whether outcome symbols are colored
    :var frames: frames the spinner cycles through
    :var outcome: outcome symbols in use
    :var print_report: whether the report is printed when finished

    """

    CLEAR_LINE = "\033[K"
    max_width = 120
    UNICODE_FRAMES: ClassVar[list[str]] = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    ASCII_FRAMES: ClassVar[list[str]] = ["|", "-", "+", "x", "*"]
    UNICODE_OUTCOME = _Outcome(ok="✔", fail="✖", skip="⚠")
    ASCII_OUTCOME = _Outcome(ok="+", fail="!", skip="?")

    def __init__(
        self,
        # keeps the existing signature
        enabled: bool = True,  # ruff:ignore[boolean-type-hint-positional-argument, boolean-default-value-positional-argument]
        refresh_rate: float = 0.1,
        # keeps the existing signature
        colored: bool = True,  # ruff:ignore[boolean-type-hint-positional-argument, boolean-default-value-positional-argument]
        stream: IO[str] | None = None,
        total: int | None = None,
    ) -> None:
        self.is_colored = colored
        self.refresh_rate = refresh_rate
        self.enabled = enabled
        stream = sys.stdout if stream is None else stream
        self.frames = self.UNICODE_FRAMES if _file_support_encoding(self.UNICODE_FRAMES, stream) else self.ASCII_FRAMES
        self.outcome = (
            self.UNICODE_OUTCOME if _file_support_encoding(self.UNICODE_OUTCOME, stream) else self.ASCII_OUTCOME
        )
        self.stream = stream
        self.total = total
        self.print_report = True

        self._envs: dict[str, float] = OrderedDict()
        self._frame_index = 0

    def __enter__(self) -> Self:
        if self.enabled:
            self.disable_cursor()
        self.render_frame()
        self._stop_spinner = threading.Event()
        self._spinner_thread = threading.Thread(target=self.render)
        self._spinner_thread.daemon = True
        self._spinner_thread.start()
        return self

    def disable_cursor(self) -> None:
        """Hide the cursor of the terminal, while the spinner is shown."""
        if self.stream.isatty():
            if sys.platform == "win32":  # pragma: win32 cover
                ci = _CursorInfo()
                handle = ctypes.windll.kernel32.GetStdHandle(-11)  # Windows-only
                ctypes.windll.kernel32.GetConsoleCursorInfo(handle, ctypes.byref(ci))  # Windows-only
                ci.visible = False
                ctypes.windll.kernel32.SetConsoleCursorInfo(handle, ctypes.byref(ci))  # Windows-only
            else:
                self.stream.write("\033[?25l")

    def render_frame(self) -> None:
        """Render the current frame of the spinner on its stream."""
        if self.enabled:
            self.clear()
            self.stream.write(f"\r{self.frame()}")

    def clear(self) -> None:
        """Clear the line the spinner is rendered on."""
        if self.enabled:
            self.stream.write("\r")
            self.stream.write(self.CLEAR_LINE)

    def frame(self) -> str:
        """Get the next frame of the spinner, and advance to the frame after it.

        :returns: the frame text, with the names of the environments that are still running

        """
        frame = self.frames[self._frame_index]
        self._frame_index += 1
        self._frame_index %= len(self.frames)
        total = f"/{self.total}" if self.total is not None else ""
        text_frame = f"[{len(self._envs)}{total}] {' | '.join(self._envs)}"
        text_frame = textwrap.shorten(text_frame, width=self.max_width - 1, placeholder="...")
        return f"{frame} {text_frame}"

    def render(self) -> Spinner:
        """Render the spinner frames until the spinner is stopped.

        :returns: the spinner

        """
        while True:
            self._stop_spinner.wait(self.refresh_rate)
            if self._stop_spinner.is_set():
                break
            self.render_frame()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if not self._stop_spinner.is_set():  # pragma: no branch  # other outcome untested
            if self._spinner_thread:  # pragma: no branch # hard to test
                self._stop_spinner.set()
                self._spinner_thread.join()

            self._frame_index = 0
            if self.enabled:
                self.clear()
                self.enable_cursor()

    def enable_cursor(self) -> None:
        """Show the cursor of the terminal again, after the spinner is done."""
        if self.stream.isatty():
            if sys.platform == "win32":  # pragma: win32 cover
                ci = _CursorInfo()
                handle = ctypes.windll.kernel32.GetStdHandle(-11)  # Windows-only
                ctypes.windll.kernel32.GetConsoleCursorInfo(handle, ctypes.byref(ci))  # Windows-only
                ci.visible = True
                ctypes.windll.kernel32.SetConsoleCursorInfo(handle, ctypes.byref(ci))  # Windows-only
            else:
                self.stream.write("\033[?25h")

    def add(self, name: str) -> None:
        """Register an environment that is running.

        :param name: the name of the environment

        """
        self._envs[name] = time.monotonic()

    def succeed(self, key: str) -> None:
        """Mark an environment as successful.

        :param key: the name of the environment

        """
        self.finalize(key, f"OK {self.outcome.ok}", str(Fore.GREEN))

    def finalize(self, key: str, status: str, color: str) -> None:
        """Mark an environment as done, with its status and duration.

        :param key: the name of the environment
        :param status: the status text to show
        :param color: the color the status is shown in

        """
        start_at = self._envs.pop(key, None)
        if self.enabled:
            self.clear()
        if self.print_report:
            duration = MISS_DURATION if start_at is None else time.monotonic() - start_at
            base = f"{key}: {status} in {td_human_readable(duration)}"
            if self.is_colored:
                base = f"{color}{base}{Fore.RESET}"
            base += os.linesep
            self.stream.write(base)

    def fail(self, key: str) -> None:
        """Mark an environment as failed.

        :param key: the name of the environment

        """
        self.finalize(key, f"FAIL {self.outcome.fail}", str(Fore.RED))

    def skip(self, key: str) -> None:
        """Mark an environment as skipped.

        :param key: the name of the environment

        """
        self.finalize(key, f"SKIP {self.outcome.skip}", str(Fore.YELLOW))


def td_human_readable(seconds: float) -> str:
    """Format a duration in seconds for people to read, such as ``2 minutes, 3.5 seconds``.

    :param seconds: the duration in seconds

    :returns: the duration as text

    """  # simplint: ignore[function-docstring] existing duration docs
    texts: list[str] = []
    periods = [
        ("day", 60 * 60 * 24),
        ("hour", 60 * 60),
        ("minute", 60),
        ("second", 1),
    ]
    for period_name, period_seconds in periods:
        period_str = None
        if period_name == "second" and (  # fixed protocol value
            seconds >= 0.01 or not texts  # ruff:ignore[magic-value-comparison]  # fixed protocol value
        ):
            period_str = f"{seconds:.2f}".rstrip("0").rstrip(".")
        elif seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            period_str = f"{period_value:.0f}"
        if period_str is not None:
            texts.append(f"{period_str} {period_name}{'' if period_str == '1' else 's'}")
    return " ".join(texts)


__all__ = [
    "MISS_DURATION",
    "Spinner",
]
