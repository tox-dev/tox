"""Execute that runs on local file system via subprocess-es"""
import logging
import os
import shutil
import sys
import time
from subprocess import DEVNULL, PIPE, TimeoutExpired
from types import TracebackType
from typing import TYPE_CHECKING, Generator, List, Optional, Sequence, Tuple, Type

from ..api import Execute, ExecuteInstance, ExecuteStatus
from ..request import ExecuteRequest, StdinSource
from ..stream import SyncWrite
from .read_via_thread import WAIT_GENERAL

if sys.platform == "win32":  # explicit check for mypy # pragma: win32 cover
    # needs stdin/stdout handlers backed by overlapped IO
    if TYPE_CHECKING:  # the typeshed libraries don't contain this, so replace it with normal one
        from subprocess import Popen
    else:
        from asyncio.windows_utils import Popen
    from signal import CTRL_C_EVENT as SIG_INTERRUPT
    from subprocess import CREATE_NEW_PROCESS_GROUP

    from .read_via_thread_windows import ReadViaThreadWindows as ReadViaThread

    CREATION_FLAGS = CREATE_NEW_PROCESS_GROUP  # a custom flag needed for Windows signal send ability (CTRL+C)
else:  # pragma: win32 no cover
    from signal import SIGINT as SIG_INTERRUPT
    from signal import SIGKILL, SIGTERM
    from subprocess import Popen

    from .read_via_thread_unix import ReadViaThreadUnix as ReadViaThread

    CREATION_FLAGS = 0

WAIT_INTERRUPT = 0.3
WAIT_TERMINATE = 0.2
IS_WIN = sys.platform == "win32"


class LocalSubProcessExecutor(Execute):
    def build_instance(self, request: ExecuteRequest, out: SyncWrite, err: SyncWrite) -> ExecuteInstance:
        return LocalSubProcessExecuteInstance(request, out, err)


class LocalSubprocessExecuteStatus(ExecuteStatus):
    def __init__(self, out: SyncWrite, err: SyncWrite, process: "Popen[bytes]"):
        self._process: "Popen[bytes]" = process
        super().__init__(out, err)
        self._interrupted = False

    @property
    def exit_code(self) -> Optional[int]:
        return self._process.returncode

    def interrupt(self) -> None:
        self._interrupted = True
        if self._process is not None:  # pragma: no branch
            # A three level stop mechanism for children - INT -> TERM -> KILL
            # communicate will wait for the app to stop, and then drain the standard streams and close them
            proc = self._process
            host_pid = os.getpid()
            to_pid = proc.pid
            logging.warning("requested interrupt of %d from %d", to_pid, host_pid)
            if proc.poll() is None:  # still alive, first INT
                logging.warning(
                    "send signal %s to %d from %d with timeout %.2f",
                    f"SIGINT({SIG_INTERRUPT})",
                    to_pid,
                    host_pid,
                    WAIT_INTERRUPT,
                )
                proc.send_signal(SIG_INTERRUPT)
                start = time.monotonic()
                while proc.poll() is None and (time.monotonic() - start) < WAIT_INTERRUPT:
                    continue
                if proc.poll() is None:  # pragma: no branch
                    if sys.platform == "win32":  # explicit check for mypy # pragma: no branch
                        logging.warning("terminate %d from %d", to_pid, host_pid)  # pragma: no cover
                    else:
                        logging.warning(
                            "send signal %s to %d from %d with timeout %.2f",
                            f"SIGTERM({SIGTERM})",
                            to_pid,
                            host_pid,
                            WAIT_TERMINATE,
                        )
                    proc.terminate()
                    start = time.monotonic()
                    if sys.platform != "win32":  # explicit check for mypy # pragma: no branch
                        # Windows terminate is UNIX kill
                        while proc.poll() is None and (time.monotonic() - start) < WAIT_TERMINATE:
                            continue
                        if proc.poll() is None:  # pragma: no branch
                            logging.warning("send signal %s to %d from %d", f"SIGKILL({SIGKILL})", to_pid, host_pid)
                            proc.kill()
                    while proc.poll() is None:
                        continue
            else:  # pragma: no cover # difficult to test, process must die just as it's being interrupted
                logging.warning("process already dead with %s within %s", proc.returncode, os.getpid())
            logging.warning("interrupt finished with success")

    def wait(self, timeout: Optional[float] = None) -> None:
        # note poll in general might deadlock if output large, but we drain in background threads so not an issue here
        try:
            self._process.wait(timeout=WAIT_GENERAL if timeout is None else timeout)
        except TimeoutExpired:
            pass

    def write_stdin(self, content: str) -> None:
        stdin = self._process.stdin
        if stdin is None:  # pragma: no branch
            return  # pragma: no cover
        bytes_content = content.encode()
        try:
            if sys.platform == "win32":  # explicit check for mypy  # pragma: win32 cover
                # on Windows we have a PipeHandle object here rather than a file stream
                import _overlapped  # type: ignore[import]

                ov = _overlapped.Overlapped(0)
                ov.WriteFile(stdin.handle, bytes_content)  # type: ignore[attr-defined]
                result = ov.getresult(10)  # wait up to 10ms to perform the operation
                if result != len(bytes_content):
                    raise RuntimeError(f"failed to write to {stdin!r}")
            else:
                stdin.write(bytes_content)
                stdin.flush()
        except OSError:  # pragma: no cover
            if self._interrupted:  # pragma: no cover
                pass  # pragma: no cover  # if the process was asked to exit in the meantime ignore write errors
            raise  # pragma: no cover

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(pid={self._process.pid}, returncode={self._process.returncode!r})"


class LocalSubprocessExecuteFailedStatus(ExecuteStatus):
    def __init__(self, out: SyncWrite, err: SyncWrite, exit_code: Optional[int]) -> None:
        super().__init__(out, err)
        self._exit_code = exit_code

    @property
    def exit_code(self) -> Optional[int]:
        return self._exit_code

    def wait(self, timeout: Optional[float] = None) -> None:
        """already dead no need to wait"""

    def write_stdin(self, content: str) -> None:
        """cannot write"""

    def interrupt(self) -> None:
        """Nothing running so nothing to interrupt"""


class LocalSubProcessExecuteInstance(ExecuteInstance):
    def __init__(
        self,
        request: ExecuteRequest,
        out: SyncWrite,
        err: SyncWrite,
        on_exit_drain: bool = True,
    ) -> None:
        super().__init__(request, out, err)
        self.process: Optional[Popen[bytes]] = None
        self._cmd: Optional[List[str]] = None
        self._read_stderr: Optional[ReadViaThread] = None
        self._read_stdout: Optional[ReadViaThread] = None
        self._on_exit_drain = on_exit_drain

    @property
    def cmd(self) -> Sequence[str]:
        if self._cmd is None:
            executable = shutil.which(self.request.cmd[0], path=self.request.env["PATH"])
            if executable is None:
                cmd = self.request.cmd  # if failed to find leave as it is
            else:
                # else use expanded format
                cmd = [executable, *self.request.cmd[1:]]
            self._cmd = cmd
        return self._cmd

    def __enter__(self) -> ExecuteStatus:
        # adjust sub-process terminal size
        columns, lines = shutil.get_terminal_size(fallback=(-1, -1))
        if columns != -1:  # pragma: no branch
            self.request.env["COLUMNS"] = str(columns)
        if columns != -1:  # pragma: no branch
            self.request.env["LINES"] = str(lines)

        stdout, stderr = self.get_stream_file_no("stdout"), self.get_stream_file_no("stderr")
        try:
            self.process = process = Popen(
                self.cmd,
                stdout=next(stdout),
                stderr=next(stderr),
                stdin={StdinSource.USER: None, StdinSource.OFF: DEVNULL, StdinSource.API: PIPE}[self.request.stdin],
                cwd=str(self.request.cwd),
                env=self.request.env,
                creationflags=CREATION_FLAGS,
            )
        except OSError as exception:
            return LocalSubprocessExecuteFailedStatus(self._out, self._err, exception.errno)

        status = LocalSubprocessExecuteStatus(self._out, self._err, process)
        drain, pid = self._on_exit_drain, self.process.pid
        self._read_stderr = ReadViaThread(stderr.send(process), self.err_handler, name=f"err-{pid}", drain=drain)
        self._read_stderr.__enter__()
        self._read_stdout = ReadViaThread(stdout.send(process), self.out_handler, name=f"out-{pid}", drain=drain)
        self._read_stdout.__enter__()

        if sys.platform == "win32":  # explicit check for mypy:  # pragma: win32 cover
            process.stderr.read = self._read_stderr._drain_stream  # type: ignore[assignment,union-attr]
            process.stdout.read = self._read_stdout._drain_stream  # type: ignore[assignment,union-attr]
        return status

    def __exit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
        if self._read_stderr is not None:
            self._read_stderr.__exit__(exc_type, exc_val, exc_tb)
        if self._read_stdout is not None:
            self._read_stdout.__exit__(exc_type, exc_val, exc_tb)

    @staticmethod
    def get_stream_file_no(key: str) -> Generator[int, "Popen[bytes]", None]:
        process = yield PIPE
        stream = getattr(process, key)
        if sys.platform == "win32":  # explicit check for mypy # pragma: win32 cover
            yield stream.handle
        else:
            yield stream.name

    def set_out_err(self, out: SyncWrite, err: SyncWrite) -> Tuple[SyncWrite, SyncWrite]:
        prev = self._out, self._err
        if self._read_stdout is not None:  # pragma: no branch
            self._read_stdout.handler = out.handler
        if self._read_stderr is not None:  # pragma: no branch
            self._read_stderr.handler = err.handler
        return prev


__all__ = (
    "SIG_INTERRUPT",
    "CREATION_FLAGS",
    "LocalSubProcessExecuteInstance",
    "LocalSubProcessExecutor",
    "LocalSubprocessExecuteStatus",
    "LocalSubprocessExecuteFailedStatus",
)
