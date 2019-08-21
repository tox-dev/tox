"""A execute that runs on local file system via subprocess-es"""
import logging
import os
import select
import shutil
import signal
import subprocess
import sys
from threading import Event, Thread
from typing import List, Optional, Sequence, Tuple, Type

from .api import ContentHandler, Execute, ExecuteInstance, ExecuteRequest, Outcome

WAIT_INTERRUPT = 0.3
WAIT_TERMINATE = 0.2
WAIT_GENERAL = 0.1


class LocalSubProcessExecutor(Execute):
    @staticmethod
    def executor() -> Type[ExecuteInstance]:
        return LocalSubProcessExecuteInstance


class LocalSubProcessExecuteInstance(ExecuteInstance):
    def __init__(
        self, request: ExecuteRequest, out_handler: ContentHandler, err_handler: ContentHandler
    ) -> None:
        super().__init__(request, out_handler, err_handler)
        self.process = None
        self._cmd = []  # type: Optional[List[str]]

    @property
    def cmd(self) -> Sequence[str]:
        if not len(self._cmd):
            executable = shutil.which(self.request.cmd[0], path=self.request.env["PATH"])
            if executable is None:
                self._cmd = self.request.cmd  # if failed to find leave as it is
            else:
                # else use expanded format
                self._cmd = [executable, *self.request.cmd[1:]]
        return self._cmd

    def run(self) -> int:
        try:
            self.process = process = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=None if self.request.allow_stdin else subprocess.PIPE,
                cwd=str(self.request.cwd),
                env=self.request.env,
                creationflags=(
                    subprocess.CREATE_NEW_PROCESS_GROUP
                    if sys.platform == "win32"
                    else 0
                    # custom flag needed for Windows signal send ability (CTRL+C)
                ),
            )
        except OSError as exception:
            exit_code = exception.errno
        else:
            with ReadViaThread(process.stderr, self.err_handler):
                with ReadViaThread(process.stdout, self.out_handler):
                    # wait it out with interruptions to allow KeyboardInterrupt on Windows
                    while process.poll() is None:
                        try:
                            # note poll in general might deadlock if output large
                            # but we drain in background threads so not an issue here
                            process.wait(timeout=WAIT_GENERAL)
                        except subprocess.TimeoutExpired:
                            continue
            exit_code = process.returncode
        return exit_code

    def interrupt(self) -> int:
        if self.process is not None:
            out, err = self._handle_interrupt()  # stop it and drain it
            self._finalize_output(err, self.err_handler, out, self.out_handler)
            return self.process.returncode
        return Outcome.OK  # pragma: no cover

    @staticmethod
    def _finalize_output(err, err_handler, out, out_handler):
        out_handler(out)
        err_handler(err)

    def _handle_interrupt(self) -> Tuple[bytes, bytes]:
        """A three level stop mechanism for children - INT -> TERM -> KILL"""
        # communicate will wait for the app to stop, and then drain the standard streams and close them
        proc = self.process
        logging.error("got KeyboardInterrupt signal")
        msg = "from {} {{}} pid {}".format(os.getpid(), proc.pid)
        if proc.poll() is None:  # still alive, first INT
            logging.warning("KeyboardInterrupt %s", msg.format("SIGINT"))
            proc.send_signal(signal.CTRL_C_EVENT if sys.platform == "win32" else signal.SIGINT)
            try:
                out, err = proc.communicate(timeout=WAIT_INTERRUPT)
            except subprocess.TimeoutExpired:  # if INT times out TERM
                logging.warning("KeyboardInterrupt %s", msg.format("SIGTERM"))
                proc.terminate()
                try:
                    out, err = proc.communicate(timeout=WAIT_INTERRUPT)
                except subprocess.TimeoutExpired:  # if TERM times out KILL
                    logging.info("KeyboardInterrupt %s", msg.format("SIGKILL"))
                    proc.kill()
                    out, err = proc.communicate()
        else:
            out, err = proc.communicate()  # just drain # pragma: no cover
        return out, err


class ReadViaThread:
    def __init__(self, stream, handler):
        self.stream = stream
        self.stop = Event()
        self.thread = Thread(target=self._read_stream)
        self.handler = handler

    def _read_stream(self):
        file_no = self.stream.fileno()
        while not (self.stream.closed or self.stop.is_set()):
            # we need to drain the stream, but periodically give chance for the thread to break if the stop event has
            # been set (this is so that an interrupt can be handled)
            if self.stream_has_data():
                data = os.read(file_no, 1)
                self.handler(data)

    def stream_has_data(self):
        # TODO: select is UNIX only supported, for WINDOWS
        # @zooba
        # You need to use overlapped IO, which is all exposed in CPython through some internal modules
        # (_winapi and _overlapped). The basic idea (and I haven't written this using those modules before) is that
        # you provide a structure that includes a thread event and Windows will trigger that event when it's done
        # But what you want may be more easily done by waiting on the file handle. I *think* that will work
        # normally for streams that don't have any data available
        # multiprocessing has some code using _overlapped to set up an overlapped pipe
        # asyncio also uses it for its subprocess support, I believe
        # Obviously since these are internal modules there's no documentation on them ;) But they do reflect the
        # Windows API calls pretty closely, so if you look up the functions on http://docs.microsoft.com
        # then you'll get all the details.
        read_available_list, _, __ = select.select([self.stream], [], [], 0.01)
        return len(read_available_list)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        thrown = None
        while True:
            try:
                self.stop.set()
                while self.thread.is_alive():
                    self.thread.join(WAIT_GENERAL)
            except KeyboardInterrupt as exception:  # pragma: no cover
                thrown = exception  # pragma: no cover
                continue  # pragma: no cover
            else:
                if thrown is not None:
                    raise thrown  # pragma: no cover
                else:  # pragma: no cover
                    break  # pragma: no cover
        if exc_val is None:  # drain what remains if we were not interrupted
            try:
                data = self.stream.read()
            except ValueError:  # pragma: no cover
                pass  # pragma: no cover
            else:
                while True:
                    try:
                        self.handler(data)
                        break
                    except KeyboardInterrupt as exception:  # pragma: no cover
                        thrown = exception  # pragma: no cover
                if thrown is not None:
                    raise thrown  # pragma: no cover
