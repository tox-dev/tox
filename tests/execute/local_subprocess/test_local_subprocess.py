import json
import logging
import os
import subprocess
import sys
from io import TextIOWrapper
from pathlib import Path
from typing import Dict, List, Tuple

import psutil
import pytest
from colorama import Fore
from psutil import AccessDenied
from pytest_mock import MockerFixture

from tox.execute.api import Outcome
from tox.execute.local_sub_process import SIG_INTERRUPT, LocalSubProcessExecutor
from tox.execute.request import ExecuteRequest, StdinSource
from tox.pytest import CaptureFixture, LogCaptureFixture, MonkeyPatch
from tox.report import NamedBytesIO


class FakeOutErr:
    def __init__(self) -> None:
        self.out_err = TextIOWrapper(NamedBytesIO("out")), TextIOWrapper(NamedBytesIO("err"))

    def read_out_err(self) -> Tuple[str, str]:
        out_got = self.out_err[0].buffer.getvalue().decode(self.out_err[0].encoding)  # type: ignore[attr-defined]
        err_got = self.out_err[1].buffer.getvalue().decode(self.out_err[1].encoding)  # type: ignore[attr-defined]
        return out_got, err_got


@pytest.mark.parametrize("color", [True, False], ids=["color", "no_color"])
@pytest.mark.parametrize(["out", "err"], [("out", "err"), ("", "")], ids=["simple", "nothing"])
@pytest.mark.parametrize("show", [True, False], ids=["show", "no_show"])
def test_local_execute_basic_pass(
    caplog: LogCaptureFixture,
    os_env: Dict[str, str],
    out: str,
    err: str,
    show: bool,
    color: bool,
) -> None:
    caplog.set_level(logging.NOTSET)
    executor = LocalSubProcessExecutor(colored=color)
    code = f"import sys; print({repr(out)}, end=''); print({repr(err)}, end='', file=sys.stderr)"
    request = ExecuteRequest(cmd=[sys.executable, "-c", code], cwd=Path(), env=os_env, stdin=StdinSource.OFF, run_id="")
    out_err = FakeOutErr()
    with executor.call(request, show=show, out_err=out_err.out_err) as status:
        while status.exit_code is None:
            status.wait()
    assert status.out == out.encode()
    assert status.err == err.encode()
    outcome = status.outcome
    assert outcome is not None
    assert bool(outcome) is True, outcome
    assert outcome.exit_code == Outcome.OK
    assert outcome.err == err
    assert outcome.out == out
    assert outcome.request == request

    out_got, err_got = out_err.read_out_err()
    if show:
        assert out_got == out
        expected = (f"{Fore.RED}{err}{Fore.RESET}" if color else err) if err else ""
        assert err_got == expected
    else:
        assert not out_got
        assert not err_got
    assert not caplog.records


def test_local_execute_basic_pass_show_on_standard_newline_flush(caplog: LogCaptureFixture) -> None:
    caplog.set_level(logging.NOTSET)
    executor = LocalSubProcessExecutor(colored=False)
    request = ExecuteRequest(
        cmd=[sys.executable, "-c", "import sys; print('out'); print('yay')"],
        cwd=Path(),
        env=os.environ.copy(),
        stdin=StdinSource.OFF,
        run_id="",
    )
    out_err = FakeOutErr()
    with executor.call(request, show=True, out_err=out_err.out_err) as status:
        while status.exit_code is None:
            status.wait()
    outcome = status.outcome
    assert outcome is not None
    assert repr(outcome)
    assert bool(outcome) is True, outcome
    assert outcome.exit_code == Outcome.OK
    assert not outcome.err
    assert outcome.out == f"out{os.linesep}yay{os.linesep}"
    out, err = out_err.read_out_err()
    assert out == f"out{os.linesep}yay{os.linesep}"
    assert not err
    assert not caplog.records


def test_local_execute_write_a_lot(caplog: LogCaptureFixture, os_env: Dict[str, str]) -> None:
    count = 10_000
    executor = LocalSubProcessExecutor(colored=False)
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
        env=os_env,
        stdin=StdinSource.OFF,
        run_id="",
    )
    out_err = FakeOutErr()
    with executor.call(request, show=False, out_err=out_err.out_err) as status:
        while status.exit_code is None:
            status.wait()
    outcome = status.outcome
    assert outcome is not None
    assert bool(outcome), outcome
    expected_out = f"{'o' * count}{os.linesep}{'b' * count}{os.linesep}"
    assert outcome.out == expected_out, expected_out[len(outcome.out) :]
    expected_err = f"{'e' * count}{os.linesep}{'a' * count}{os.linesep}"
    assert outcome.err == expected_err, expected_err[len(outcome.err) :]


def test_local_execute_basic_fail(capsys: CaptureFixture, caplog: LogCaptureFixture, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.chdir(Path(__file__).parents[3])
    caplog.set_level(logging.NOTSET)
    executor = LocalSubProcessExecutor(colored=False)
    cwd = Path().absolute()
    cmd = [
        sys.executable,
        "-c",
        "import sys; print('out', end=''); print('err', file=sys.stderr, end=''); sys.exit(3)",
    ]
    request = ExecuteRequest(cmd=cmd, cwd=cwd, env=os.environ.copy(), stdin=StdinSource.OFF, run_id="")

    # run test
    out_err = FakeOutErr()
    with executor.call(request, show=False, out_err=out_err.out_err) as status:
        while status.exit_code is None:
            status.wait()
    outcome = status.outcome
    assert outcome is not None

    assert repr(outcome)

    # assert no output, no logs
    out, err = out_err.read_out_err()
    assert not out
    assert not err
    assert not caplog.records

    # assert return object
    assert bool(outcome) is False, outcome
    assert outcome.exit_code == 3
    assert outcome.err == "err"
    assert outcome.out == "out"
    assert outcome.request == request

    # asset fail
    with pytest.raises(SystemExit) as context:
        outcome.assert_success()
    # asset fail
    assert context.value.code == 3

    out, err = capsys.readouterr()
    assert out == "out\n"
    expected = f"{Fore.RED}err{Fore.RESET}\n"
    assert err == expected

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelno == logging.CRITICAL
    assert record.msg == "exit %s (%.2f seconds) %s> %s"
    _code, _duration, _cwd, _cmd = record.args
    assert _code == 3
    assert _cwd == cwd
    assert _cmd == request.shell_cmd
    assert isinstance(_duration, float)
    assert _duration > 0


def test_command_does_not_exist(capsys: CaptureFixture, caplog: LogCaptureFixture, os_env: Dict[str, str]) -> None:
    caplog.set_level(logging.NOTSET)
    executor = LocalSubProcessExecutor(colored=False)
    request = ExecuteRequest(
        cmd=["sys-must-be-missing"], cwd=Path().absolute(), env=os_env, stdin=StdinSource.OFF, run_id=""
    )
    out_err = FakeOutErr()
    with executor.call(request, show=False, out_err=out_err.out_err) as status:
        while status.exit_code is None:  # pragma: no branch
            status.wait()  # pragma: no cover
    outcome = status.outcome
    assert outcome is not None

    assert bool(outcome) is False, outcome
    assert outcome.exit_code != Outcome.OK
    assert outcome.out == ""
    assert outcome.err == ""
    assert not caplog.records


@pytest.mark.skipif(sys.platform == "win32", reason="You need a conhost shell for keyboard interrupt")
def test_command_keyboard_interrupt(tmp_path: Path, monkeypatch: MonkeyPatch, capfd: CaptureFixture) -> None:
    monkeypatch.chdir(tmp_path)
    process_up_signal = tmp_path / "signal"
    cmd = [sys.executable, str(Path(__file__).parent / "local_subprocess_sigint.py"), str(process_up_signal)]
    process = subprocess.Popen(cmd)
    while not process_up_signal.exists():
        assert process.poll() is None
    root = process.pid
    try:
        child = next(iter(psutil.Process(pid=root).children())).pid
    except AccessDenied as exc:  # pragma: no cover # on termux for example
        pytest.skip(str(exc))  # pragma: no cover

    print(f"test running in {os.getpid()} and sending CTRL+C to {process.pid}", file=sys.stderr)
    process.send_signal(SIG_INTERRUPT)
    try:
        process.communicate(timeout=3)
    except subprocess.TimeoutExpired:  # pragma: no cover
        process.kill()
        raise

    out, err = capfd.readouterr()
    assert f"W	requested interrupt of {child} from {root}" in err, err
    assert f"W	send signal SIGINT(2) to {child} from {root} with timeout 0.30" in err, err
    assert f"W	send signal SIGTERM(15) to {child} from {root} with timeout 0.20" in err, err
    assert f"W	send signal SIGKILL(9) to {child} from {root}" in err, err

    outs = out.split("\n")

    exit_code = int(outs[0])
    assert exit_code == -9
    assert float(outs[3]) > 0  # duration
    assert "how about no signal 2" in outs[1], outs[1]  # 2 - Interrupt
    assert "how about no signal 15" in outs[1], outs[1]  # 15 - Terminated


@pytest.mark.parametrize("tty_mode", ["on", "off"])
def test_local_subprocess_tty(monkeypatch: MonkeyPatch, mocker: MockerFixture, tty_mode: str) -> None:
    monkeypatch.setenv("COLUMNS", "100")
    monkeypatch.setenv("LINES", "100")
    tty = tty_mode == "on"
    mocker.patch("sys.stdout.isatty", return_value=tty)
    mocker.patch("sys.stderr.isatty", return_value=tty)

    executor = LocalSubProcessExecutor(colored=False)
    cmd: List[str] = [sys.executable, str(Path(__file__).parent / "tty_check.py")]
    request = ExecuteRequest(cmd=cmd, stdin=StdinSource.API, cwd=Path.cwd(), env=dict(os.environ), run_id="")
    out_err = FakeOutErr()
    with executor.call(request, show=False, out_err=out_err.out_err) as status:
        while status.exit_code is None:
            status.wait()
    outcome = status.outcome
    assert outcome is not None

    assert outcome
    info = json.loads(outcome.out)
    assert info == {
        "stdout": False,
        "stderr": False,
        "stdin": False,
        "terminal": [100, 100],
    }
