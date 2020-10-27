"""
Abstract base API for executing commands within tox environments.
"""
import logging
import signal
import sys
import threading
from abc import ABC, abstractmethod
from functools import partial
from timeit import default_timer as timer
from typing import Callable, NoReturn, Sequence, Type

from colorama import Fore

from .request import ExecuteRequest
from .stream import CollectWrite

ContentHandler = Callable[[bytes], None]
Executor = Callable[[ExecuteRequest, ContentHandler, ContentHandler], int]
if sys.platform == "win32":
    SIGINT = signal.CTRL_C_EVENT
else:
    SIGINT = signal.SIGINT


class Execute(ABC):
    """Abstract API for execution of a tox environment"""

    def __call__(self, request: ExecuteRequest, show_on_standard: bool, colored: bool) -> "Outcome":
        start = timer()
        executor = self.executor()
        interrupt = None

        try:
            with CollectWrite(sys.stdout.buffer if show_on_standard else None) as out:
                error_color = Fore.RED if colored else None
                with CollectWrite(sys.stderr.buffer if show_on_standard else None, error_color) as err:
                    instance: ExecuteInstance = executor(request, out.collect, err.collect)
                    try:
                        exit_code = instance.run()
                    except KeyboardInterrupt as exception:
                        interrupt = exception
                        while True:
                            try:
                                is_main = threading.current_thread() == threading.main_thread()
                                if is_main:
                                    # disable further interrupts until we finish this, main thread only
                                    if sys.platform != "win32":
                                        signal.signal(SIGINT, signal.SIG_IGN)
                            except KeyboardInterrupt:  # pragma: no cover
                                continue  # pragma: no cover
                            else:
                                try:
                                    exit_code = instance.interrupt()
                                    break
                                finally:
                                    if is_main and sys.platform != "win32":  # restore signal handler on main thread
                                        signal.signal(SIGINT, signal.default_int_handler)
        finally:
            end = timer()
        result = Outcome(request, show_on_standard, exit_code, out.text, err.text, start, end, instance.cmd)
        if interrupt is not None:
            raise ToxKeyboardInterrupt(result, interrupt)
        return result

    @staticmethod
    @abstractmethod
    def executor() -> Type["ExecuteInstance"]:
        raise NotImplementedError


class ExecuteInstance:
    """An instance of a command execution"""

    def __init__(self, request: ExecuteRequest, out_handler: ContentHandler, err_handler: ContentHandler) -> None:
        def _safe_handler(handler: Callable[[bytes], None], data: bytes) -> None:
            try:
                handler(data)
            except Exception:  # noqa # pragma: no cover
                pass  # pragma: no cover

        self.request = request
        self.out_handler = partial(_safe_handler, out_handler)
        self.err_handler = partial(_safe_handler, err_handler)

    @abstractmethod
    def run(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def interrupt(self) -> int:
        raise NotImplementedError

    @property
    @abstractmethod
    def cmd(self) -> Sequence[str]:
        raise NotImplementedError


class Outcome:
    """Result of a command execution"""

    OK = 0

    def __init__(
        self,
        request: ExecuteRequest,
        show_on_standard: bool,
        exit_code: int,
        out: str,
        err: str,
        start: float,
        end: float,
        cmd: Sequence[str],
    ):
        self.request = request
        self.show_on_standard = show_on_standard
        self.exit_code = exit_code
        self.out = out
        self.err = err
        self.start = start
        self.end = end
        self.cmd = cmd

    def __bool__(self) -> bool:
        return self.exit_code == self.OK

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}: exit {self.exit_code} in {self.elapsed:.2f}ms for {self.request.shell_cmd}"

    def assert_success(self, logger: logging.Logger) -> None:
        if self.exit_code != self.OK:
            self._assert_fail(logger)
        self.log_run_done(logging.INFO, logger)

    def _assert_fail(self, logger: logging.Logger) -> NoReturn:
        if self.show_on_standard is False:
            if self.out:
                print(self.out, file=sys.stdout)
            if self.err:
                print(Fore.RED, file=sys.stderr, end="")
                print(self.err, file=sys.stderr, end="")
                print(Fore.RESET, file=sys.stderr)
        self.log_run_done(logging.CRITICAL, logger)
        raise SystemExit(self.exit_code)

    def log_run_done(self, lvl: int, logger: logging.Logger) -> None:
        req = self.request
        logger.log(lvl, "exit %d (%.2fs) %s> %s", self.exit_code, self.elapsed, req.cwd, req.shell_cmd)

    @property
    def elapsed(self) -> float:
        return self.end - self.start


class ToxKeyboardInterrupt(KeyboardInterrupt):
    def __init__(self, outcome: Outcome, exc: KeyboardInterrupt):
        self.outcome = outcome
        self.exc = exc


__all__ = (
    "ContentHandler",
    "SIGINT",
    "Outcome",
    "ToxKeyboardInterrupt",
    "Execute",
    "ExecuteInstance",
)
