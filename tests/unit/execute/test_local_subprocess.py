import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import psutil
import pytest
from colorama import Fore

from tox.execute.api import SIGINT, Outcome
from tox.execute.local_sub_process import CREATION_FLAGS, LocalSubProcessExecutor
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
    outcome = executor.__call__(request, show_on_standard=False, colored=False)
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
    outcome = executor.__call__(request, show_on_standard=True, colored=True)
    assert bool(outcome) is True
    assert outcome.exit_code == Outcome.OK
    assert outcome.err == "err"
    assert outcome.out == "out"
    out, err = capsys.readouterr()
    assert out == "out"
    expected = f"{Fore.RED}err{Fore.RESET}"
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
    outcome = executor.__call__(request, show_on_standard=True, colored=False)
    assert bool(outcome) is True
    assert outcome.exit_code == Outcome.OK
    assert not outcome.err
    assert outcome.out == f"out{os.linesep}yay{os.linesep}"
    out, err = capsys.readouterr()
    assert out == f"out{os.linesep}yay{os.linesep}"
    assert not err
    assert not caplog.records


def test_local_execute_write_a_lot(capsys, caplog):
    count = 10000
    executor = LocalSubProcessExecutor()
    request = ExecuteRequest(
        cmd=[
            sys.executable,
            "-c",
            (
                "import sys; import time; from datetime import datetime; import os;"
                "print('e' * {0}, file=sys.stderr);"
                "print('o' * {0}, file=sys.stdout);"
                "time.sleep(0.5);"
                "print('a' * {0}, file=sys.stderr);"
                "print('b' * {0}, file=sys.stdout);"
            ).format(count),
        ],
        cwd=Path(),
        env=os.environ,
        allow_stdin=False,
    )
    outcome = executor.__call__(request, show_on_standard=False, colored=False)
    assert bool(outcome)
    expected_out = f"{'o' * count}{os.linesep}{'b' * count}{os.linesep}"
    assert outcome.out == expected_out
    expected_err = f"{'e' * count}{os.linesep}{'a' * count}{os.linesep}"
    assert outcome.err == expected_err


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
    outcome = executor.__call__(request, show_on_standard=False, colored=False)

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
    expected = f"{Fore.RED}err{Fore.RESET}\n"
    assert err == expected

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelno == logging.CRITICAL
    assert record.msg == "exit %d (%.2fs) cwd %s: %s"
    _code, _duration, _cwd, _cmd = record.args
    assert _code == 3
    assert _cwd == cwd
    assert _cmd == request.shell_cmd
    assert isinstance(_duration, float)
    assert _duration > 0


def test_command_does_not_exist(capsys, caplog):
    caplog.set_level(logging.NOTSET)
    executor = LocalSubProcessExecutor()
    request = ExecuteRequest(cmd=["sys-must-be-missing"], cwd=Path().absolute(), env=os.environ, allow_stdin=False)
    outcome = executor.__call__(request, show_on_standard=False, colored=False)

    assert bool(outcome) is False
    assert outcome.exit_code != Outcome.OK
    assert outcome.out == ""
    assert outcome.err == ""
    assert not caplog.records


@pytest.mark.skipif(sys.platform == "win32", reason="TODO: find out why it does not work")
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
        creationflags=CREATION_FLAGS,
    )
    while not send_signal.exists():
        assert process.poll() is None

    root = process.pid
    child = next(iter(psutil.Process(pid=root).children())).pid
    process.send_signal(SIGINT)
    try:
        out, err = process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        out, err = process.communicate()
        assert False, f"{out}\n{err}"

    assert "ERROR:root:got KeyboardInterrupt signal" in err, err
    assert f"WARNING:root:KeyboardInterrupt from {root} SIGINT pid {child}" in err, err
    assert f"WARNING:root:KeyboardInterrupt from {root} SIGTERM pid {child}" in err, err
    assert f"INFO:root:KeyboardInterrupt from {root} SIGKILL pid {child}" in err, err

    outs = out.split("\n")

    exit_code = int(outs[0])
    assert exit_code == -9
    assert float(outs[3]) > 0  # duration
    assert "how about no signal 15" in outs[1], outs[1]  # stdout
    assert "how about no KeyboardInterrupt" in outs[2], outs[2]  # stderr


@pytest.mark.parametrize("tty_mode", ["on", "off"])
def test_local_subprocess__tty(monkeypatch, mocker, tty_mode):
    monkeypatch.setenv("COLUMNS", "100")
    monkeypatch.setenv("LINES", "100")
    tty = tty_mode == "on"
    mocker.patch("sys.stdout.isatty", return_value=tty)
    mocker.patch("sys.stderr.isatty", return_value=tty)

    executor = LocalSubProcessExecutor()
    cmd = [sys.executable, Path(__file__).parent / "tty_check.py"]
    request = ExecuteRequest(cmd=cmd, allow_stdin=True, cwd=Path.cwd(), env=dict(os.environ))
    outcome = executor.__call__(request, show_on_standard=False, colored=False)

    assert outcome
    info = json.loads(outcome.out)

    assert info == {
        "stdout": tty,
        "stderr": tty,
        "stdin": False,
        "terminal": [100, 100],
    }
