"""Handle reporting from within tox."""

from __future__ import annotations

import locale
import logging
import os
import sys
from contextlib import contextmanager
from io import BytesIO, TextIOWrapper
from pathlib import Path
from threading import Thread, current_thread, local
from threading import enumerate as enumerate_threads
from typing import TYPE_CHECKING, ClassVar, Final, cast
from weakref import WeakKeyDictionary

from colorama import Fore, Style, init
from virtualenv.util.subprocess import LogCmd

from .util.redact import redact_value
from .util.typing_compat import override

if TYPE_CHECKING:
    from collections.abc import Generator, MutableMapping

LEVELS: Final[dict[int, int]] = {
    0: logging.CRITICAL,
    1: logging.ERROR,
    2: logging.WARNING,
    3: logging.INFO,
    4: logging.DEBUG,
    5: logging.NOTSET,
}

MAX_LEVEL: Final[int] = max(LEVELS.keys())
LOGGER: Final[logging.Logger] = logging.getLogger()
OutErr = tuple[TextIOWrapper, TextIOWrapper]


_THREAD_PARENT_IDENT: Final[MutableMapping[Thread, int | None]] = WeakKeyDictionary()


class _LogThreadLocal(local):
    # A thread local variable that inherits values from its parent.
    _ident_to_data: ClassVar[dict[int | None, str]] = {}

    def __init__(self, out_err: OutErr) -> None:
        self.name = self._ident_to_data.get(_THREAD_PARENT_IDENT.get(current_thread()), "ROOT")
        self.out_err = out_err

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

        for ident in self._ident_to_data.keys() - {t.ident for t in enumerate_threads()}:
            self._ident_to_data.pop(ident)
        self._ident_to_data[current_thread().ident] = value

    @staticmethod
    @contextmanager
    def patch_thread() -> Generator[None, None, None]:
        # CPython has no parent thread tracking, monkey-patch needed https://github.com/python/cpython/issues/86718
        def new_start(self: Thread) -> None:
            _THREAD_PARENT_IDENT[self] = current_thread().ident
            old_start(self)

        old_start = Thread.start
        Thread.start = new_start  # type: ignore[method-assign] # no typed way to swap a method, and CPython offers no hook to track the parent thread
        try:
            yield
        finally:
            Thread.start = old_start  # type: ignore[method-assign] # no typed way to swap a method, and CPython offers no hook to track the parent thread

    @contextmanager
    def with_name(self, name: str) -> Generator[None, None, None]:
        previous, self.name = self.name, name
        try:
            yield
        finally:
            self.name = previous

    @contextmanager
    def suspend_out_err(  # keeps the signature
        self,
        yes: bool,  # ruff:ignore[boolean-type-hint-positional-argument]  # keeps the signature
        out_err: OutErr | None = None,  # keeps the signature
    ) -> Generator[OutErr, None, None]:
        previous_out, previous_err = self.out_err
        if yes:
            if out_err is None:  # pragma: no branch  # other outcome untested
                out = self._make(f"out-{self.name}", previous_out)
                err = self._make(f"err-{self.name}", previous_err)
            else:
                out, err = out_err  # pragma: no cover  # setup not built by tests
            self.out_err = out, err
        try:
            yield self.out_err
        finally:
            if yes:
                self.out_err = previous_out, previous_err

    @staticmethod
    def _make(prefix: str, based_of: TextIOWrapper) -> TextIOWrapper:
        return TextIOWrapper(
            NamedBytesIO(f"{prefix}-{based_of.name}"),
            encoding=locale.getpreferredencoding(do_setlocale=False),
            errors="backslashreplace",
        )


class NamedBytesIO(BytesIO):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name: str = name


if TYPE_CHECKING:
    _STREAM_HANDLER_BASE = logging.StreamHandler[TextIOWrapper]
else:
    _STREAM_HANDLER_BASE = logging.StreamHandler  # at runtime StreamHandler is not subscriptable


class ToxHandler(_STREAM_HANDLER_BASE):
    """Controls tox output.

    :param level: the minimum level of the messages to show
    :param is_colored: whether the messages are colored
    :param out_err: the standard output and error streams to write to

    """

    def __init__(  # keeps the signature
        self,
        level: int,
        is_colored: bool,  # ruff:ignore[boolean-type-hint-positional-argument]  # keeps the signature
        out_err: OutErr,  # keeps the signature
    ) -> None:
        self._local = _LogThreadLocal(out_err)
        super().__init__(stream=self.stdout)
        if is_colored:
            init()
        self._is_colored = is_colored
        self._setup_level(is_colored, level)

    @property
    def stdout(self) -> TextIOWrapper:
        """The current standard output."""
        return self._local.out_err[0]

    def _setup_level(  # keeps the signature
        self,
        is_colored: bool,  # ruff:ignore[boolean-type-hint-positional-argument]  # keeps the signature
        level: int,  # keeps the signature
    ) -> None:
        self.setLevel(level)
        self._error_formatter = self._get_formatter(logging.ERROR, level, is_colored)
        self._warning_formatter = self._get_formatter(logging.WARNING, level, is_colored)
        self._remaining_formatter = self._get_formatter(logging.INFO, level, is_colored)

    @staticmethod
    def _get_formatter(  # keeps the signature
        level: int,
        enabled_level: int,
        is_colored: bool,  # ruff:ignore[boolean-type-hint-positional-argument]  # keeps the signature
    ) -> logging.Formatter:
        color = ""
        if is_colored:
            if level >= logging.ERROR:
                color = Fore.RED
            elif level >= logging.WARNING:
                color = Fore.CYAN
            else:
                color = Fore.WHITE

        def _c(val: str) -> str:
            return val if color else ""

        fmt = f"{color} %(message)s{_c(Style.RESET_ALL)}"
        if enabled_level <= logging.DEBUG:
            fmt = (
                f"{_c(Fore.GREEN)} %(relativeCreated)d %(levelname).1s{_c(Style.RESET_ALL)}{fmt}{_c(Style.DIM)}"
                f" [%(pathname)s:%(lineno)d]{_c(Style.RESET_ALL)}"
            )
        fmt = f"{_c(Style.BRIGHT)}{_c(Fore.MAGENTA)}%(env_name)s:{_c(Style.RESET_ALL)}{fmt}"
        return logging.Formatter(fmt)

    @property
    @override
    def name(self) -> str:  # pyrefly: ignore[bad-override] # the value follows the active tox env so it must be a property, pyrefly rejects that over a typeshed attribute: https://github.com/facebook/pyrefly/issues/2771
        """The current tox environment name."""
        return self._local.name  # pragma: no cover  # untested error path

    @name.setter
    @override
    def name(self, value: str | None) -> None:
        """
        Ignore anyone changing this, the name always reflects the active tox environment.

        :param value: the ignored name
        """

    @property
    @override
    def stream(self) -> TextIOWrapper:  # pyrefly: ignore[bad-override] # the value follows the active tox env so it must be a property, pyrefly rejects that over a typeshed attribute: https://github.com/facebook/pyrefly/issues/2771
        """The current stream to write to, an alias for the current standard output."""
        return self.stdout

    @stream.setter
    @override
    def stream(self, value: TextIOWrapper) -> None:
        """
        Ignore anyone changing this.

        :param value: the ignored stream
        """

    @contextmanager
    def with_context(self, name: str) -> Generator[None, None, None]:
        """Set a new tox environment context.

        :param name: the name of the tox environment

        :yields: nothing, the messages in the block are tagged with the name

        """
        with self._local.with_name(name):
            yield

    @contextmanager
    def suspend_out_err(  # keeps the signature
        self,
        yes: bool,  # ruff:ignore[boolean-type-hint-positional-argument]  # keeps the signature
        out_err: OutErr | None = None,  # keeps the signature
    ) -> Generator[OutErr, None, None]:
        with self._local.suspend_out_err(yes, out_err) as out_err_res:
            yield out_err_res

    def write_out_err(self, out_err: tuple[bytes, bytes]) -> None:
        # read/write through the buffer as we collect bytes to print bytes (no transcoding needed)
        self.stdout.buffer.write(out_err[0])
        self.stderr.buffer.write(out_err[1])

    @property
    def stderr(self) -> TextIOWrapper:
        """The current standard error."""
        return self._local.out_err[1]

    @override
    def format(self, record: logging.LogRecord) -> str:
        if record.name == "virtualenv.seed.embed.pip_invoke" and isinstance(record.args, tuple):
            record.args = tuple(
                LogCmd(arg.cmd, {name: redact_value(name, value) for name, value in arg.env.items()})
                if isinstance(arg, LogCmd) and arg.env is not None
                else arg
                for arg in record.args
            )
        # shorten the pathname to start from within the site-packages folder
        record.env_name = "root" if self._local.name is None else self._local.name
        basename = str(Path(record.pathname).parent)
        record.pathname = record.pathname[max((len(p) for p in sys.path if basename.startswith(p)), default=-1) + 1 :]

        if record.levelno >= logging.ERROR:
            return self._error_formatter.format(record)
        if record.levelno >= logging.WARNING:
            if self._is_colored and record.msg == "%s%s> %s" and record.args:
                record.msg = f"%s{Style.NORMAL}%s{Style.DIM}>{Style.RESET_ALL} %s"
            return self._warning_formatter.format(record)
        return self._remaining_formatter.format(record)

    @staticmethod
    @contextmanager
    def patch_thread() -> Generator[None, None, None]:
        with _LogThreadLocal.patch_thread():
            yield

    def update_verbosity(self, verbosity: int) -> None:
        level = _get_level(verbosity)
        LOGGER.setLevel(level)
        self._setup_level(self._is_colored, level)


def setup_report(  # keeps the signature
    verbosity: int,
    is_colored: bool,  # ruff:ignore[boolean-type-hint-positional-argument]  # keeps the signature
) -> ToxHandler:
    for std_stream in (sys.stdout, sys.stderr):
        if isinstance(std_stream, TextIOWrapper):
            # Redirected Windows streams may use code pages that cannot encode tox output.
            std_stream.reconfigure(errors="backslashreplace")
    _clean_handlers(LOGGER)
    level = _get_level(verbosity)
    LOGGER.setLevel(level)
    for name in ("distlib.util", "filelock"):
        logging.getLogger(name).disabled = True
    out_err: OutErr = cast("OutErr", (sys.stdout, sys.stderr))
    handler = ToxHandler(level, is_colored, out_err)
    LOGGER.addHandler(handler)
    logging.debug("setup logging to %s on pid %s", logging.getLevelName(level), os.getpid())
    return handler


def _clean_handlers(log: logging.Logger) -> None:
    for log_handler in list(log.handlers):  # remove handlers of libraries
        log.removeHandler(log_handler)


def _get_level(verbosity: int) -> int:
    return LEVELS[min(verbosity, MAX_LEVEL)]


class HandledError(RuntimeError):
    """Error that has been handled so no need for stack trace."""


__all__ = [
    "LEVELS",
    "LOGGER",
    "HandledError",
    "NamedBytesIO",
    "OutErr",
    "ToxHandler",
    "setup_report",
]
