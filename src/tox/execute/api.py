"""
Abstract base API for executing commands within tox environments.
"""
import logging
import sys
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from types import TracebackType
from typing import Callable, Iterator, NoReturn, Optional, Sequence, Tuple, Type

from colorama import Fore

from tox.report import OutErr

from .request import ExecuteRequest, StdinSource
from .stream import SyncWrite

ContentHandler = Callable[[bytes], None]
Executor = Callable[[ExecuteRequest, ContentHandler, ContentHandler], int]
LOGGER = logging.getLogger(__name__)


class ExecuteStatus(ABC):
    def __init__(self, out: SyncWrite, err: SyncWrite) -> None:
        self.outcome: Optional[Outcome] = None
        self._out = out
        self._err = err

    @property
    @abstractmethod
    def exit_code(self) -> Optional[int]:
        raise NotImplementedError

    @abstractmethod
    def wait(self, timeout: Optional[float] = None) -> None:
        raise NotImplementedError

    @abstractmethod
    def write_stdin(self, content: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def interrupt(self) -> None:
        raise NotImplementedError

    def set_out_err(self, out: SyncWrite, err: SyncWrite) -> Tuple[SyncWrite, SyncWrite]:
        res = self._out, self._err
        self._out, self._err = out, err
        return res

    @property
    def out(self) -> bytearray:
        return self._out.content

    @property
    def err(self) -> bytearray:
        return self._err.content


class Execute(ABC):
    """Abstract API for execution of a tox environment"""

    def __init__(self, colored: bool) -> None:
        self._colored = colored

    @contextmanager
    def call(self, request: ExecuteRequest, show: bool, out_err: OutErr) -> Iterator[ExecuteStatus]:
        start = time.monotonic()
        try:
            # collector is what forwards the content from the file streams to the standard streams
            out, err = out_err[0].buffer, out_err[1].buffer
            out_sync = SyncWrite(out.name, out if show else None)
            err_sync = SyncWrite(err.name, err if show else None, Fore.RED if self._colored else None)
            with out_sync, err_sync:
                instance = self.build_instance(request, out_sync, err_sync)
                with instance as status:
                    yield status
                exit_code = status.exit_code
        finally:
            end = time.monotonic()
        status.outcome = Outcome(request, show, exit_code, out_sync.text, err_sync.text, start, end, instance.cmd)

    @abstractmethod
    def build_instance(self, request: ExecuteRequest, out: SyncWrite, err: SyncWrite) -> "ExecuteInstance":
        raise NotImplementedError


class ExecuteInstance(ABC):
    """An instance of a command execution"""

    def __init__(self, request: ExecuteRequest, out: SyncWrite, err: SyncWrite) -> None:
        self.request = request
        self._out = out
        self._err = err

    @property
    def out_handler(self) -> ContentHandler:
        return self._out.handler

    @property
    def err_handler(self) -> ContentHandler:
        return self._err.handler

    @abstractmethod
    def __enter__(self) -> ExecuteStatus:
        raise NotImplementedError

    @abstractmethod
    def __exit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
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
        exit_code: Optional[int],
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
        return (
            f"{self.__class__.__name__}: exit {self.exit_code} in {self.elapsed:.2f} seconds"
            f" for {self.request.shell_cmd}"
        )

    def assert_success(self) -> None:
        if self.exit_code is not None and self.exit_code != self.OK:
            self._assert_fail()
        self.log_run_done(logging.INFO)

    def _assert_fail(self) -> NoReturn:
        if self.show_on_standard is False:
            if self.out:
                sys.stdout.write(self.out)
                if not self.out.endswith("\n"):
                    sys.stdout.write("\n")
            if self.err:
                sys.stderr.write(Fore.RED)
                sys.stderr.write(self.err)
                sys.stderr.write(Fore.RESET)
                if not self.err.endswith("\n"):
                    sys.stderr.write("\n")
        self.log_run_done(logging.CRITICAL)
        raise SystemExit(self.exit_code)

    def log_run_done(self, lvl: int) -> None:
        req = self.request
        LOGGER.log(lvl, "exit %s (%.2f seconds) %s> %s", self.exit_code, self.elapsed, req.cwd, req.shell_cmd)

    @property
    def elapsed(self) -> float:
        return self.end - self.start

    def out_err(self) -> Tuple[str, str]:
        return self.out, self.err


__all__ = (
    "ContentHandler",
    "Outcome",
    "Execute",
    "ExecuteInstance",
    "ExecuteStatus",
    "StdinSource",
)
