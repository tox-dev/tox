"""Abstract base API for executing commands within tox environments."""

from __future__ import annotations

import logging
import sys
import time
from abc import ABC, abstractmethod
from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager, suppress
from typing import IO, TYPE_CHECKING, Final, NoReturn, cast

from colorama import Fore

from tox.util.typing_compat import override

from .request import ExecuteRequest, StdinSource
from .stream import SyncWrite

if TYPE_CHECKING:
    from types import TracebackType

    from tox.report import OutErr
    from tox.tox_env.api import ToxEnv
    from tox.util.json_types import JsonValue

ContentHandler = Callable[[bytes], int]
"""Callback that receives a chunk of the output of a command, and returns the number of bytes it handled."""
Executor = Callable[[ExecuteRequest, ContentHandler, ContentHandler], int]
LOGGER: Final[logging.Logger] = logging.getLogger(__name__)  # simplint: ignore[SMP404]  # imported by tox plugins


class ExecuteOptions:
    """The options that control how a command execution is stopped and whether its output is captured.

    :param env: the environment the command runs in

    """

    def __init__(self, env: ToxEnv) -> None:
        self._env = env

    @property
    def suicide_timeout(self) -> float:
        """Seconds to wait for the process to exit on its own before sending SIGINT."""
        return cast("float", self._env.conf["suicide_timeout"])

    @property
    def interrupt_timeout(self) -> float:
        """Seconds to wait after SIGINT before sending SIGTERM."""
        return cast("float", self._env.conf["interrupt_timeout"])

    @property
    def terminate_timeout(self) -> float:
        """Seconds to wait after SIGTERM before sending SIGKILL."""
        return cast("float", self._env.conf["terminate_timeout"])

    @property
    def no_capture(self) -> bool:
        """Whether the output is shown as it is produced, instead of only being captured."""
        return cast("bool", getattr(self._env.options, "no_capture", False))

    @classmethod
    def register_conf(cls, env: ToxEnv) -> None:
        """Register the configuration keys that control how the execution is stopped.

        :param env: the environment to register the keys in

        """
        env.conf.add_config(
            keys=["suicide_timeout"],
            desc="timeout to allow process to exit before sending SIGINT",
            of_type=float,
            default=0.0,
        )
        env.conf.add_config(
            keys=["interrupt_timeout"],
            desc="timeout before sending SIGTERM after SIGINT",
            of_type=float,
            default=0.3,
        )
        env.conf.add_config(
            keys=["terminate_timeout"],
            desc="timeout before sending SIGKILL after SIGTERM",
            of_type=float,
            default=0.2,
        )


class ExecuteStatus(ABC):
    """The state of a command execution while it runs, and its outcome once it is done.

    :param options: the options of the execution
    :param out: the stream the standard output is written to
    :param err: the stream the standard error is written to

    :var outcome: the outcome of the execution, ``None`` until it is done

    """

    def __init__(self, options: ExecuteOptions, out: SyncWrite, err: SyncWrite) -> None:
        self.outcome: Outcome | None = None
        self.options = options
        self._out = out
        self._err = err

    @property
    @abstractmethod
    def exit_code(self) -> int | None:
        """The exit code of the command, ``None`` while it runs."""
        raise NotImplementedError

    @property
    def start_error(self) -> BaseException | None:
        """The error that kept the command from starting, ``None`` once it started."""
        return None

    @property
    def out(self) -> bytearray:
        """The standard output collected so far."""
        return self._out.content

    @property
    def err(self) -> bytearray:
        """The standard error collected so far."""
        return self._err.content

    @property
    def metadata(self) -> dict[str, JsonValue]:
        """Metadata about the execution, empty unless the executor provides some."""
        return {}

    @abstractmethod
    def wait(self, timeout: float | None = None) -> int | None:
        """Wait for the command to finish.

        :param timeout: the seconds to wait, wait without a limit when ``None``

        :returns: the exit code, or ``None`` when the command did not finish in time

        """
        raise NotImplementedError

    @abstractmethod
    def write_stdin(self, content: str) -> None:
        """Write content to the standard input of the command.

        :param content: the content to write

        """
        raise NotImplementedError

    @abstractmethod
    def interrupt(self) -> None:
        """Interrupt the command."""
        raise NotImplementedError

    def set_out_err(self, out: SyncWrite, err: SyncWrite) -> tuple[SyncWrite, SyncWrite]:
        """Replace the streams the output of the command is written to.

        :param out: the new standard output stream
        :param err: the new standard error stream

        :returns: the previous standard output and standard error streams

        """
        res = self._out, self._err
        self._out, self._err = out, err
        return res


class FinishedExecuteStatus(ExecuteStatus):
    """Report a fixed exit code for a command that finished or never started, without running a process.

    :param options: the execution options of the command
    :param out: the sink for the standard output
    :param err: the sink for the standard error
    :param exit_code: the exit code to report, ``None`` if there is none

    """

    def __init__(self, options: ExecuteOptions, out: SyncWrite, err: SyncWrite, exit_code: int | None) -> None:
        super().__init__(options, out, err)
        self._exit_code = exit_code

    @property
    @override
    def exit_code(self) -> int | None:
        return self._exit_code

    @override
    def wait(self, timeout: float | None = None) -> int | None:
        return self._exit_code

    @override
    def write_stdin(self, content: str) -> None:
        """Cannot write.

        :param content: the text that would be written to the standard input

        """

    @override
    def interrupt(self) -> None:
        return None  # nothing running so nothing to interrupt


class Execute(ABC):
    """Abstract API for execution of a tox environment.

    :param colored: whether the output is colored

    """

    _option_class: type[ExecuteOptions] = ExecuteOptions

    def __init__(  # keeps the signature
        self,
        colored: bool,  # ruff:ignore[boolean-type-hint-positional-argument]  # keeps the signature
    ) -> None:
        self._colored = colored

    @contextmanager
    def call(
        self,
        request: ExecuteRequest,
        show: bool,  # ruff:ignore[boolean-type-hint-positional-argument]  # keeps the signature
        out_err: OutErr,
        env: ToxEnv,
    ) -> Generator[ExecuteStatus, None, None]:
        """Run a request, and yield the status of the execution while it runs.

        :param request: the request to run
        :param show: whether to show the output while the request runs
        :param out_err: the standard output and standard error streams to write to
        :param env: the environment the request runs in

        :yields: the status of the execution

        """
        start = time.monotonic()
        stderr_color = None
        if self._colored:
            try:
                stderr_color = getattr(Fore, env.options.stderr_color)
            except (AttributeError, KeyError, TypeError):  # many tests have a mocked 'env'
                stderr_color = Fore.RED
            if sys.platform == "win32" and show:
                try:
                    # Windows-only import
                    from colorama.winterm import enable_vt_processing  # ruff:ignore[import-outside-top-level]

                    for stream in out_err:
                        with suppress(AttributeError, OSError):
                            enable_vt_processing(stream.buffer.fileno())  # pragma: win32 cover
                except ImportError:
                    pass
        # collector is what forwards the content from the file streams to the standard streams
        out = cast("IO[bytes]", out_err[0].buffer)
        err = cast("IO[bytes]", out_err[1].buffer)
        out_sync = SyncWrite(out.name, out if show else None)
        err_sync = SyncWrite(err.name, err if show else None, str(stderr_color) if stderr_color is not None else None)
        try:
            with out_sync, err_sync:
                instance = self.build_instance(request, self._option_class(env), out_sync, err_sync)
                with instance as status:
                    yield status
                exit_code = status.exit_code
        finally:
            end = time.monotonic()
        status.outcome = Outcome(
            request,
            show,
            exit_code,
            out_sync.text,
            err_sync.text,
            start,
            end,
            instance.cmd,
            status.metadata,
            status.start_error,
        )

    @abstractmethod
    def build_instance(
        self,
        request: ExecuteRequest,
        options: ExecuteOptions,
        out: SyncWrite,
        err: SyncWrite,
    ) -> ExecuteInstance:
        """Build the instance that runs a request.

        :param request: the request to run
        :param options: the options of the execution
        :param out: the stream the standard output is written to
        :param err: the stream the standard error is written to

        :returns: the instance that runs the request

        """
        raise NotImplementedError

    @classmethod
    def register_conf(cls, env: ToxEnv) -> None:
        """Register the configuration keys of the execution options.

        :param env: the environment to register the keys in

        """
        cls._option_class.register_conf(env)


class ExecuteInstance(ABC):
    """An instance of a command execution.

    :param request: the command to execute
    :param options: the execution options of the command
    :param out: the sink for the standard output
    :param err: the sink for the standard error

    """

    def __init__(self, request: ExecuteRequest, options: ExecuteOptions, out: SyncWrite, err: SyncWrite) -> None:
        self.request = request
        self.options = options
        self._out = out
        self._err = err

    @abstractmethod
    def __enter__(self) -> ExecuteStatus:
        raise NotImplementedError

    @abstractmethod
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        raise NotImplementedError

    @property
    def out_handler(self) -> ContentHandler:
        """The callback that receives the standard output of the command."""
        return self._out.handler

    @property
    def err_handler(self) -> ContentHandler:
        """The callback that receives the standard error of the command."""
        return self._err.handler

    @property
    @abstractmethod
    def cmd(self) -> Sequence[str]:
        """The command line to run."""
        raise NotImplementedError


class Outcome:
    """Result of a command execution.

    :var OK: the exit code of a successful command

    """

    OK = 0
    FAILED = 1  #: exit code reported when a ``!`` command exits with :attr:`OK`

    def __init__(  # ruff:ignore[too-many-arguments]  # public signature
        self,
        request: ExecuteRequest,
        show_on_standard: bool,  # ruff:ignore[boolean-type-hint-positional-argument]  # keeps the signature
        exit_code: int | None,
        out: str,
        err: str,
        start: float,
        end: float,
        cmd: Sequence[str],
        metadata: dict[str, JsonValue],
        start_error: BaseException | None = None,
    ) -> None:
        """Create a new execution outcome.

        :param request: the execution request
        :param show_on_standard: a flag indicating if the execution was shown on stdout/stderr
        :param exit_code: the exit code for the execution
        :param out: the standard output of the execution
        :param err: the standard error of the execution
        :param start: a timer sample for the start of the execution
        :param end: a timer sample for the end of the execution
        :param cmd: the command as executed
        :param metadata: additional metadata attached to the execution
        :param start_error: the error that kept the command from starting, ``None`` once it started

        """
        self.request = request  #: the execution request
        self.show_on_standard = show_on_standard  #: a flag indicating if the execution was shown on stdout/stderr
        self.exit_code = exit_code  #: the exit code for the execution
        self.out = out  #: the standard output of the execution
        self.err = err  #: the standard error of the execution
        self.start = start  #: a timer sample for the start of the execution
        self.end = end  #: a timer sample for the end of the execution
        self.cmd = cmd  #: the command as executed
        self.metadata = metadata  #: additional metadata attached to the execution
        self.start_error = start_error  #: the error that kept the command from starting, ``None`` once it started

    def __bool__(self) -> bool:
        return self.exit_code == self.OK

    @override
    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}: exit {self.exit_code} in {self.elapsed:.2f} seconds"
            f" for {self.request.shell_cmd_redacted}"
        )

    @property
    def elapsed(self) -> float:
        """The time the execution took, in seconds."""
        return self.end - self.start

    def assert_success(self) -> None:
        """Assert that the execution succeeded."""
        if self.start_error is not None or self.exit_code not in {None, self.OK}:
            self._assert_fail(self.exit_code or self.FAILED)
        self.log_run_done(logging.INFO)

    def _assert_fail(self, code: int) -> NoReturn:
        if self.show_on_standard is False:
            if self.out:
                sys.stdout.write(self.out)
                if not self.out.endswith("\n"):
                    sys.stdout.write("\n")
            if self.err:
                sys.stderr.write(str(Fore.RED))
                sys.stderr.write(self.err)
                sys.stderr.write(str(Fore.RESET))
                if not self.err.endswith("\n"):
                    sys.stderr.write("\n")
        self.log_run_done(logging.CRITICAL)
        raise SystemExit(code)

    def log_run_done(self, lvl: int) -> None:
        """Log that the run was done.

        :param lvl: the level on what to log as interpreted by :func:`logging.log`

        """
        req = self.request
        metadata = ""
        if self.metadata:
            metadata = f" {', '.join(f'{k}={v}' for k, v in self.metadata.items())}"
        LOGGER.log(
            lvl,
            "exit %s (%.2f seconds) %s> %s%s",
            self.exit_code,
            self.elapsed,
            req.cwd,
            req.shell_cmd_redacted,
            metadata,
        )

    def assert_failure(self) -> None:
        """Assert that the execution failed."""
        if self.start_error is not None or self.exit_code == self.OK:  # never started, so nothing to invert
            self._assert_fail(self.exit_code or self.FAILED)
        self.log_run_done(logging.INFO)

    def out_err(self) -> tuple[str, str]:
        """:returns: a tuple of the standard output and standard error"""
        return self.out, self.err


__all__ = [
    "ContentHandler",
    "Execute",
    "ExecuteInstance",
    "ExecuteOptions",
    "ExecuteStatus",
    "FinishedExecuteStatus",
    "Outcome",
    "StdinSource",
]
