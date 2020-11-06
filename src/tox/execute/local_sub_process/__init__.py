"""Execute that runs on local file system via subprocess-es"""
import logging
import os
import shutil
import sys
from subprocess import PIPE, TimeoutExpired
from typing import TYPE_CHECKING, Dict, Generator, List, Optional, Sequence, Type

from ..api import SIGINT, ContentHandler, Execute, ExecuteInstance, Outcome
from ..request import ExecuteRequest
from .read_via_thread import WAIT_GENERAL

if sys.platform == "win32":  # pragma: win32 cover
    # needs stdin/stdout handlers backed by overlapped IO
    if TYPE_CHECKING:  # the typeshed libraries don't contain this, so replace it with normal one
        from subprocess import Popen
    else:
        from asyncio.windows_utils import Popen
    from subprocess import CREATE_NEW_PROCESS_GROUP

    from .read_via_thread_windows import ReadViaThreadWindows as ReadViaThread

    CREATION_FLAGS = CREATE_NEW_PROCESS_GROUP  # a custom flag needed for Windows signal send ability (CTRL+C)

else:  # pragma: win32 no cover
    from subprocess import Popen

    from .read_via_thread_unix import ReadViaThreadUnix as ReadViaThread

    CREATION_FLAGS = 0


WAIT_INTERRUPT = 0.3
WAIT_TERMINATE = 0.2


class LocalSubProcessExecutor(Execute):
    @staticmethod
    def executor() -> Type[ExecuteInstance]:
        return LocalSubProcessExecuteInstance


class LocalSubProcessExecuteInstance(ExecuteInstance):
    def __init__(self, request: ExecuteRequest, out_handler: ContentHandler, err_handler: ContentHandler) -> None:
        super().__init__(request, out_handler, err_handler)
        self.process: Optional[Popen[bytes]] = None
        self._cmd: Optional[List[str]] = None
        self._env: Optional[Dict[str, str]] = None

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

    @property
    def env(self) -> Dict[str, str]:
        if self._env is None:  # pragma: no branch
            # terminal size don't pass through, if set , use the environment variables per shutil.get_terminal_size
            env = self.request.env.copy()
            columns, lines = shutil.get_terminal_size(fallback=(-1, -1))  # if cannot get (-1) do not set env-vars
            if columns != -1:  # pragma: no branch # no easy way to control get_terminal_size without env-vars
                env["COLUMNS"] = str(columns)
            if columns != 1:  # pragma: no branch # no easy way to control get_terminal_size without env-vars
                env["LINES"] = str(lines)
            self._env = env
        return self._env

    def run(self) -> int:
        stdout, stderr = self.get_stream_file_no("stdout"), self.get_stream_file_no("stderr")
        try:
            self.process = process = Popen(
                self.cmd,
                stdout=next(stdout),
                stderr=next(stderr),
                stdin=None if self.request.allow_stdin else PIPE,
                cwd=str(self.request.cwd),
                env=self.env,
                creationflags=CREATION_FLAGS,
            )
        except OSError as exception:
            exit_code = exception.errno
        else:
            with ReadViaThread(stderr.send(process), self.err_handler) as read_stderr:
                with ReadViaThread(stdout.send(process), self.out_handler) as read_stdout:
                    if sys.platform == "win32":  # pragma: win32 cover
                        process.stderr.read = read_stderr._drain_stream  # type: ignore[assignment,union-attr]
                        process.stdout.read = read_stdout._drain_stream  # type: ignore[assignment,union-attr]
                    # wait it out with interruptions to allow KeyboardInterrupt on Windows
                    while process.poll() is None:
                        try:
                            # note poll in general might deadlock if output large
                            # but we drain in background threads so not an issue here
                            process.wait(timeout=WAIT_GENERAL)
                        except TimeoutExpired:
                            continue
            exit_code = process.returncode
        return exit_code

    @staticmethod
    def get_stream_file_no(key: str) -> Generator[int, "Popen[bytes]", None]:
        if sys.platform != "win32" and getattr(sys, key).isatty():  # pragma: win32 no cover
            # on UNIX if tty is set let's forward it via a pseudo terminal
            import pty

            main, child = pty.openpty()
            yield child
            os.close(child)
            yield main
        else:
            process = yield PIPE
            stream = getattr(process, key)
            if sys.platform == "win32":  # pragma: win32 cover
                yield stream.handle
            else:
                yield stream.name

    def interrupt(self) -> int:
        if self.process is not None:
            # A three level stop mechanism for children - INT -> TERM -> KILL
            # communicate will wait for the app to stop, and then drain the standard streams and close them
            proc = self.process
            logging.error("got KeyboardInterrupt signal")
            msg = f"from {os.getpid()} {{}} pid {proc.pid}"
            if proc.poll() is None:  # still alive, first INT
                logging.warning("KeyboardInterrupt %s", msg.format("SIGINT"))
                proc.send_signal(SIGINT)
                try:
                    out, err = proc.communicate(timeout=WAIT_INTERRUPT)
                except TimeoutExpired:  # if INT times out TERM
                    logging.warning("KeyboardInterrupt %s", msg.format("SIGTERM"))
                    proc.terminate()
                    try:
                        out, err = proc.communicate(timeout=WAIT_INTERRUPT)
                    except TimeoutExpired:  # if TERM times out KILL
                        logging.info("KeyboardInterrupt %s", msg.format("SIGKILL"))
                        proc.kill()
                        out, err = proc.communicate()
            else:  # pragma: no cover # difficult to test, process must die just as it's being interrupted
                try:
                    out, err = proc.communicate()  # just drain
                except ValueError:  # if already drained via another communicate
                    out, err = b"", b""
            self.out_handler(out)
            self.err_handler(err)
            return int(self.process.returncode)
        return Outcome.OK  # pragma: no cover
