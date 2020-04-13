import logging
import os
import signal
import subprocess
import sys
from pathlib import Path

import psutil
import pytest
from colorama import Fore

from tox.execute.api import Outcome
from tox.execute.local_sub_process import LocalSubProcessExecutor
from tox.execute.request import ExecuteRequest


def test_local_execute_basic_pass(capsys, caplog):
    caplog.set_level(logging.NOTSET)
    executor = LocalSubProcessExecutor()
    request = ExecuteRequest(
        cmd=[sys.executable, "-c", "import sys; print('out', end=''); print('err', end='', file=sys.stderr)"],
        cwd=Path(),
        env=os.environ,
        allow_stdin=False,
    )
    outcome = executor.__call__(request, show_on_standard=False)
    assert bool(outcome) is True
    assert outcome.exit_code == Outcome.OK
    assert outcome.err == "err"
    assert outcome.out == "out"
    assert outcome.request == request
    out, err = capsys.readouterr()
    assert not out
    assert not err
    assert not caplog.records


def test_local_execute_basic_pass_show_on_standard(capsys, caplog):
    caplog.set_level(logging.NOTSET)
    executor = LocalSubProcessExecutor()
    request = ExecuteRequest(
        cmd=[sys.executable, "-c", "import sys; print('out', end=''); print('err', end='', file=sys.stderr)"],
        cwd=Path(),
        env=os.environ,
        allow_stdin=False,
    )
    outcome = executor.__call__(request, show_on_standard=True)
    assert bool(outcome) is True
    assert outcome.exit_code == Outcome.OK
    assert outcome.err == "err"
    assert outcome.out == "out"
    out, err = capsys.readouterr()
    assert out == "out"
    expected = "{}err{}".format(Fore.RED, Fore.RESET)
    assert err == expected
    assert not caplog.records


def test_local_execute_basic_pass_show_on_standard_newline_flush(capsys, caplog):
    caplog.set_level(logging.NOTSET)
    executor = LocalSubProcessExecutor()
    request = ExecuteRequest(
        cmd=[sys.executable, "-c", "import sys; print('out'); print('yay')"],
        cwd=Path(),
        env=os.environ,
        allow_stdin=False,
    )
    outcome = executor.__call__(request, show_on_standard=True)
    assert bool(outcome) is True
    assert outcome.exit_code == Outcome.OK
    assert not outcome.err
    assert outcome.out == "out{0}yay{0}".format(os.linesep)
    out, err = capsys.readouterr()
    assert out == "out{0}yay{0}".format(os.linesep)
    assert not err
    assert not caplog.records


def test_local_execute_write_a_lot(capsys, caplog):
    count = 8192
    executor = LocalSubProcessExecutor()
    request = ExecuteRequest(
        cmd=[
            sys.executable,
            "-c",
            (
                "import sys; import time;"
                "print('e' * {0}, file=sys.stderr, end=''); print('o' * {0}, file=sys.stdout, end='');"
                "time.sleep(0.5);"
                "print('e' * {0}, file=sys.stderr, end=''); print('o' * {0}, file=sys.stdout, end='');"
            ).format(count),
        ],
        cwd=Path(),
        env=os.environ,
        allow_stdin=False,
    )
    outcome = executor.__call__(request, show_on_standard=False)
    assert bool(outcome)
    assert outcome.out == "o" * (count * 2)
    assert outcome.err == "e" * (count * 2)


def test_local_execute_basic_fail(caplog, capsys):
    caplog.set_level(logging.NOTSET)
    executor = LocalSubProcessExecutor()
    cwd = Path().absolute()
    cmd = [
        sys.executable,
        "-c",
        "import sys; print('out', end=''); print('err', file=sys.stderr, end=''); sys.exit(3)",
    ]
    request = ExecuteRequest(cmd=cmd, cwd=cwd, env=os.environ, allow_stdin=False)

    # run test
    outcome = executor.__call__(request, show_on_standard=False)

    # assert no output, no logs
    out, err = capsys.readouterr()
    assert not out
    assert not err
    assert not caplog.records

    # assert return object
    assert bool(outcome) is False
    assert outcome.exit_code == 3
    assert outcome.err == "err"
    assert outcome.out == "out"
    assert outcome.request == request

    # asset fail
    logger = logging.getLogger(__name__)
    with pytest.raises(SystemExit) as context:
        outcome.assert_success(logger)
    # asset fail
    assert context.value.code == 3

    out, err = capsys.readouterr()
    assert out == "out\n"
    expected = "{}err{}\n".format(Fore.RED, Fore.RESET)
    assert err == expected

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelno == logging.CRITICAL
    assert record.msg == "exit code %d for %s: %s in %s"
    _code, _cwd, _cmd, _duration = record.args
    assert _code == 3
    assert _cwd == cwd
    assert _cmd == request.shell_cmd
    assert isinstance(_duration, float)
    assert _duration > 0


def test_command_does_not_exist(capsys, caplog):
    caplog.set_level(logging.NOTSET)
    executor = LocalSubProcessExecutor()
    request = ExecuteRequest(
        cmd=["sys-must-be-missing".format(sys.executable)], cwd=Path().absolute(), env=os.environ, allow_stdin=False,
    )
    outcome = executor.__call__(request, show_on_standard=False)

    assert bool(outcome) is False
    assert outcome.exit_code != Outcome.OK
    assert outcome.out == ""
    assert outcome.err == ""
    assert not caplog.records


def test_command_keyboard_interrupt(tmp_path):
    send_signal = tmp_path / "send"
    process = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).parent / "local_subprocess_sigint.py"),
            str(tmp_path / "idle"),
            str(send_signal),
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )
    while not send_signal.exists():
        assert process.poll() is None

    root = process.pid
    child = next(iter(psutil.Process(pid=root).children())).pid
    process.send_signal(signal.SIGINT)
    out, err = process.communicate()

    assert "ERROR:root:got KeyboardInterrupt signal" in err, err
    assert "WARNING:root:KeyboardInterrupt from {} SIGINT pid {}".format(root, child) in err, err
    assert "WARNING:root:KeyboardInterrupt from {} SIGTERM pid {}".format(root, child) in err, err
    assert "INFO:root:KeyboardInterrupt from {} SIGKILL pid {}".format(root, child) in err, err

    outs = out.split("\n")

    exit_code = int(outs[0])
    assert exit_code == -9
    assert float(outs[3]) > 0  # duration
    assert "how about no signal 15" in outs[1], outs[1]  # stdout
    assert "how about no KeyboardInterrupt" in outs[2], outs[2]  # stderr
