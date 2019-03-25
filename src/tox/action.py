from __future__ import absolute_import, unicode_literals

import os
import pipes
import signal
import subprocess
import sys
import time
from contextlib import contextmanager
from threading import Thread

import py

from tox import reporter
from tox.constants import INFO
from tox.exception import InvocationError
from tox.util.lock import get_unique_file
from tox.util.stdlib import is_main_thread

WAIT_INTERRUPT = 0.3
WAIT_TERMINATE = 0.2


class Action(object):
    """Action is an effort to group operations with the same goal (within reporting)"""

    def __init__(self, name, msg, args, log_dir, generate_tox_log, command_log, popen, python):
        self.name = name
        self.args = args
        self.msg = msg
        self.activity = self.msg.split(" ", 1)[0]
        self.log_dir = log_dir
        self.generate_tox_log = generate_tox_log
        self.via_popen = popen
        self.command_log = command_log
        self._timed_report = None
        self.python = python

    def __enter__(self):
        msg = "{} {}".format(self.msg, " ".join(map(str, self.args)))
        self._timed_report = reporter.timed_operation(self.name, msg)
        self._timed_report.__enter__()

        return self

    def __exit__(self, type, value, traceback):
        self._timed_report.__exit__(type, value, traceback)

    def setactivity(self, name, msg):
        self.activity = name
        if msg:
            reporter.verbosity0("{} {}: {}".format(self.name, name, msg), bold=True)
        else:
            reporter.verbosity1("{} {}: {}".format(self.name, name, msg), bold=True)

    def info(self, name, msg):
        reporter.verbosity1("{} {}: {}".format(self.name, name, msg), bold=True)

    def popen(
        self,
        args,
        cwd=None,
        env=None,
        redirect=True,
        returnout=False,
        ignore_ret=False,
        capture_err=True,
        callback=None,
    ):
        """this drives an interaction with a subprocess"""
        cmd_args = [str(x) for x in args]
        cmd_args_shell = " ".join(pipes.quote(i) for i in cmd_args)
        stream_getter = self._get_standard_streams(
            capture_err, cmd_args_shell, redirect, returnout
        )
        cwd = os.getcwd() if cwd is None else cwd
        with stream_getter as (fin, out_path, stderr, stdout):
            args = self._rewrite_args(cwd, args)
            try:
                process = self.via_popen(
                    args,
                    stdout=stdout,
                    stderr=stderr,
                    cwd=str(cwd),
                    env=os.environ.copy() if env is None else env,
                    universal_newlines=True,
                    shell=False,
                    creationflags=(
                        subprocess.CREATE_NEW_PROCESS_GROUP
                        if sys.platform == "win32"
                        else 0
                        # needed for Windows signal send ability (CTRL+C)
                    ),
                )
            except OSError as e:
                reporter.error(
                    "invocation failed (errno {:d}), args: {}, cwd: {}".format(
                        e.errno, cmd_args_shell, cwd
                    )
                )
                raise
            if callback is not None:
                callback(process)
            reporter.log_popen(cwd, out_path, cmd_args_shell, process.pid)

            output = self.evaluate_cmd(fin, process, redirect)
        exit_code = process.returncode
        if exit_code and not ignore_ret:
            if out_path:
                reporter.error(
                    "invocation failed (exit code {:d}), logfile: {}".format(exit_code, out_path)
                )
                output = out_path.read()
                reporter.error(output)
                self.command_log.add_command(args, output, exit_code)
                raise InvocationError(cmd_args_shell, exit_code, out_path)
            else:
                raise InvocationError(cmd_args_shell, exit_code)
        if not output and out_path:
            output = out_path.read()
        self.command_log.add_command(args, output, exit_code)
        return output

    def evaluate_cmd(self, input_file_handler, process, redirect):
        try:
            if self.generate_tox_log and not redirect:
                if process.stderr is not None:
                    # prevent deadlock
                    raise ValueError("stderr must not be piped here")
                # we read binary from the process and must write using a binary stream
                buf = getattr(sys.stdout, "buffer", sys.stdout)
                last_time = time.time()
                while True:
                    # we have to read one byte at a time, otherwise there
                    # might be no output for a long time with slow tests
                    data = input_file_handler.read(1)
                    if data:
                        buf.write(data)
                        if b"\n" in data or (time.time() - last_time) > 1:
                            # we flush on newlines or after 1 second to
                            # provide quick enough feedback to the user
                            # when printing a dot per test
                            buf.flush()
                            last_time = time.time()
                    elif process.poll() is not None:
                        if process.stdout is not None:
                            process.stdout.close()
                        break
                    else:
                        time.sleep(0.1)
                        # the seek updates internal read buffers
                        input_file_handler.seek(0, 1)
                input_file_handler.close()
            out, _ = process.communicate()  # wait to finish
        except KeyboardInterrupt as exception:
            main_thread = is_main_thread()
            while True:
                try:
                    if main_thread:
                        # spin up a new thread to disable further interrupt on main thread
                        stopper = Thread(target=self.handle_interrupt, args=(process,))
                        stopper.start()
                        stopper.join()
                    else:
                        self.handle_interrupt(process)
                except KeyboardInterrupt:
                    continue
                break
            raise exception
        return out

    def handle_interrupt(self, process):
        """A three level stop mechanism for children - INT -> TERM -> KILL"""
        msg = "from {} {{}} pid {}".format(os.getpid(), process.pid)
        if process.poll() is None:
            self.info("KeyboardInterrupt", msg.format("SIGINT"))
            process.send_signal(signal.CTRL_C_EVENT if sys.platform == "win32" else signal.SIGINT)
            if self._wait(process, WAIT_INTERRUPT) is None:
                self.info("KeyboardInterrupt", msg.format("SIGTERM"))
                process.terminate()
                if self._wait(process, WAIT_TERMINATE) is None:
                    self.info("KeyboardInterrupt", msg.format("SIGKILL"))
                    process.kill()
                    process.communicate()

    @staticmethod
    def _wait(process, timeout):
        if sys.version_info >= (3, 3):
            # python 3 has timeout feature built-in
            try:
                process.communicate(timeout=WAIT_INTERRUPT)
            except subprocess.TimeoutExpired:
                pass
        else:
            # on Python 2 we need to simulate it
            delay = 0.01
            while process.poll() is None and timeout > 0:
                time.sleep(delay)
                timeout -= delay
        return process.poll()

    @contextmanager
    def _get_standard_streams(self, capture_err, cmd_args_shell, redirect, returnout):
        stdout = out_path = input_file_handler = None
        stderr = subprocess.STDOUT if capture_err else None

        if self.generate_tox_log or redirect:
            out_path = self.get_log_path(self.name)
            with out_path.open("wt") as stdout, out_path.open("rb") as input_file_handler:
                stdout.write(
                    "actionid: {}\nmsg: {}\ncmdargs: {!r}\n\n".format(
                        self.name, self.msg, cmd_args_shell
                    )
                )
                stdout.flush()
                input_file_handler.read()  # read the header, so it won't be written to stdout

                yield input_file_handler, out_path, stderr, stdout
                return

        if returnout:
            stdout = subprocess.PIPE

        yield input_file_handler, out_path, stderr, stdout

    def get_log_path(self, actionid):
        log_file = get_unique_file(self.log_dir, prefix=actionid, suffix=".log")
        return log_file

    def _rewrite_args(self, cwd, args):
        new_args = []
        cwd = py.path.local(cwd)
        for arg in args:
            arg_path = py.path.local(arg)
            if arg_path.exists():
                arg = cwd.bestrelpath(arg)
            new_args.append(str(arg))
        # subprocess does not always take kindly to .py scripts so adding the interpreter here
        if INFO.IS_WIN:
            ext = os.path.splitext(str(new_args[0]))[1].lower()
            if ext == ".py":
                new_args = [str(self.python)] + new_args
        return new_args
