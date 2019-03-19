from __future__ import absolute_import, unicode_literals

import os
import pipes
import signal
import subprocess
import sys
import time
from contextlib import contextmanager

import py

from tox import reporter
from tox.constants import INFO
from tox.exception import InvocationError
from tox.util.lock import get_unique_file


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
    ):
        """this drives an interaction with a subprocess"""
        cmd_args = [str(x) for x in args]
        cmd_args_shell = " ".join(pipes.quote(i) for i in cmd_args)
        stream_getter = self._get_standard_streams(
            capture_err, cmd_args_shell, redirect, returnout
        )
        cwd = os.getcwd() if cwd is None else cwd
        with stream_getter as (fin, out_path, stderr, stdout):
            try:
                args = self._rewrite_args(cwd, args)
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
            reporter.log_popen(cwd, out_path, cmd_args_shell)
            output = self.feed_stdin(fin, process, redirect)
            exit_code = process.wait()
        if exit_code and not ignore_ret:
            invoked = " ".join(map(str, args))
            if out_path:
                reporter.error(
                    "invocation failed (exit code {:d}), logfile: {}".format(exit_code, out_path)
                )
                output = out_path.read()
                reporter.error(output)
                self.command_log.add_command(args, output, exit_code)
                raise InvocationError(invoked, exit_code, out_path)
            else:
                raise InvocationError(invoked, exit_code)
        if not output and out_path:
            output = out_path.read()
        self.command_log.add_command(args, output, exit_code)
        return output

    def feed_stdin(self, fin, process, redirect):
        try:
            if self.generate_tox_log and not redirect:
                if process.stderr is not None:
                    # prevent deadlock
                    raise ValueError("stderr must not be piped here")
                # we read binary from the process and must write using a binary stream
                buf = getattr(sys.stdout, "buffer", sys.stdout)
                out = None
                last_time = time.time()
                while True:
                    # we have to read one byte at a time, otherwise there
                    # might be no output for a long time with slow tests
                    data = fin.read(1)
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
                        fin.seek(0, 1)
                fin.close()
            else:
                out, err = process.communicate()
        except KeyboardInterrupt:
            process.send_signal(signal.CTRL_C_EVENT if sys.platform == "win32" else signal.SIGINT)
            try:
                process.wait(0.1)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait()
            raise
        return out

    @contextmanager
    def _get_standard_streams(self, capture_err, cmd_args_shell, redirect, returnout):
        stdout = out_path = fin = None
        stderr = subprocess.STDOUT if capture_err else None

        if self.generate_tox_log or redirect:
            out_path = self.get_log_path(self.name)
            with out_path.open("wt") as stdout, out_path.open("rb") as fin:
                stdout.write(
                    "actionid: {}\nmsg: {}\ncmdargs: {!r}\n\n".format(
                        self.name, self.msg, cmd_args_shell
                    )
                )
                stdout.flush()
                fin.read()  # read the header, so it won't be written to stdout

                yield fin, out_path, stderr, stdout
                return

        if returnout:
            stdout = subprocess.PIPE

        yield fin, out_path, stderr, stdout

    def get_log_path(self, actionid):
        return get_unique_file(
            self.log_dir, prefix=actionid, suffix=".logs", report=reporter.verbosity1
        )

    def _rewrite_args(self, cwd, args):
        new_args = []
        for arg in args:
            if not INFO.IS_WIN and isinstance(arg, py.path.local):
                cwd = py.path.local(cwd)
                arg = cwd.bestrelpath(arg)
            new_args.append(str(arg))
        # subprocess does not always take kindly to .py scripts so adding the interpreter here
        if INFO.IS_WIN:
            ext = os.path.splitext(str(new_args[0]))[1].lower()
            if ext == ".py":
                new_args = [str(self.python)] + new_args
        return new_args
