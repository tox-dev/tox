from __future__ import annotations

import json
import locale
import logging
import os
import shutil
import stat
import subprocess
import sys
from io import TextIOWrapper
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, create_autospec

import psutil
import pytest
from colorama import Fore
from psutil import AccessDenied

from tox.execute.api import ExecuteOptions, Outcome
from tox.execute.local_sub_process import SIG_INTERRUPT, LocalSubProcessExecuteInstance, LocalSubProcessExecutor
from tox.execute.local_sub_process.read_via_thread_unix import ReadViaThreadUnix
from tox.execute.request import ExecuteRequest, StdinSource
from tox.execute.stream import SyncWrite
from tox.report import NamedBytesIO

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from tox.pytest import CaptureFixture, LogCaptureFixture, MonkeyPatch


class FakeOutErr:
    def __init__(self) -> None:
        self.out_err = (
            TextIOWrapper(NamedBytesIO("out"), encoding=locale.getpreferredencoding(False)),
            TextIOWrapper(NamedBytesIO("err"), encoding=locale.getpreferredencoding(False)),
        )

    def read_out_err(self) -> tuple[str, str]:
        out_got = self.out_err[0].buffer.getvalue().decode(self.out_err[0].encoding)  # type: ignore[attr-defined]
        err_got = self.out_err[1].buffer.getvalue().decode(self.out_err[1].encoding)  # type: ignore[attr-defined]
        return out_got, err_got


@pytest.mark.parametrize("color", [True, False], ids=["color", "no_color"])
@pytest.mark.parametrize(("out", "err"), [("out", "err"), ("", "")], ids=["simple", "nothing"])
@pytest.mark.parametrize("show", [True, False], ids=["show", "no_show"])
def test_local_execute_basic_pass(  # noqa: PLR0913
    caplog: LogCaptureFixture,
    os_env: dict[str, str],
    out: str,
    err: str,
    show: bool,
    color: bool,
) -> None:
    caplog.set_level(logging.NOTSET)
    executor = LocalSubProcessExecutor(colored=color)
    code = f"import sys; print({out!r}, end=''); print({err!r}, end='', file=sys.stderr)"
    request = ExecuteRequest(cmd=[sys.executable, "-c", code], cwd=Path(), env=os_env, stdin=StdinSource.OFF, run_id="")
    out_err = FakeOutErr()
    with executor.call(request, show=show, out_err=out_err.out_err, env=MagicMock()) as status:
        while status.exit_code is None:  # pragma: no branch
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
    with executor.call(request, show=True, out_err=out_err.out_err, env=MagicMock()) as status:
        while status.exit_code is None:  # pragma: no branch
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


def test_local_execute_write_a_lot(os_env: dict[str, str]) -> None:
    count = 10_000
    executor = LocalSubProcessExecutor(colored=False)
    request = ExecuteRequest(
        cmd=[
            sys.executable,
            "-c",
            (
                "import sys; import time; from datetime import datetime; import os;"
                f"print('e' * {count}, file=sys.stderr);"
                f"print('o' * {count}, file=sys.stdout);"
                "time.sleep(0.5);"
                f"print('a' * {count}, file=sys.stderr);"
                f"print('b' * {count}, file=sys.stdout);"
            ),
        ],
        cwd=Path(),
        env=os_env,
        stdin=StdinSource.OFF,
        run_id="",
    )
    out_err = FakeOutErr()
    with executor.call(request, show=False, out_err=out_err.out_err, env=MagicMock()) as status:
        while status.exit_code is None:  # pragma: no branch
            status.wait()
    outcome = status.outcome
    assert outcome is not None
    assert bool(outcome), outcome
    expected_out = f"{'o' * count}{os.linesep}{'b' * count}{os.linesep}"
    assert outcome.out == expected_out, expected_out[len(outcome.out) :]
    expected_err = f"{'e' * count}{os.linesep}{'a' * count}{os.linesep}"
    assert outcome.err == expected_err, expected_err[len(outcome.err) :]


@pytest.mark.skipif(sys.platform == "win32", reason="Unix terminal size test")
def test_local_execute_terminal_size(os_env: dict[str, str], monkeypatch: MonkeyPatch) -> None:
    """Regression test for #2999 - check terminal size is set correctly in tox subprocess."""
    import pty  # noqa: PLC0415

    terminal_size = os.terminal_size((84, 42))
    main, child = pty.openpty()  # type: ignore[attr-defined, unused-ignore]
    # Use ReadViaThreadUnix to help with debugging the test itself.
    pipe_out = ReadViaThreadUnix(main, sys.stdout.buffer.write, name="testout", drain=True)  # type: ignore[arg-type]
    with pipe_out, monkeypatch.context() as monkey, open(  # noqa: PTH123
        child, "w", encoding=locale.getpreferredencoding(False)
    ) as stdout_mock:
        # Switch stdout with test pty
        monkey.setattr(sys, "stdout", stdout_mock)
        monkey.setenv("COLUMNS", "84")
        monkey.setenv("LINES", "42")

        executor = LocalSubProcessExecutor(colored=False)
        request = ExecuteRequest(
            cmd=[sys.executable, "-c", "import os; print(os.get_terminal_size())"],
            cwd=Path(),
            env=os_env,
            stdin=StdinSource.OFF,
            run_id="",
        )
        out_err = FakeOutErr()
        with executor.call(request, show=False, out_err=out_err.out_err, env=MagicMock()) as status:
            while status.exit_code is None:  # pragma: no branch
                status.wait()
    outcome = status.outcome
    assert outcome is not None
    assert bool(outcome), outcome
    expected_out = f"{terminal_size!r}\r\n"
    assert outcome.out == expected_out, expected_out[len(outcome.out) :]
    assert not outcome.err


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
    with executor.call(request, show=False, out_err=out_err.out_err, env=MagicMock()) as status:
        while status.exit_code is None:  # pragma: no branch
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
    assert record.msg == "exit %s (%.2f seconds) %s> %s%s"
    assert record.args is not None
    _code, _duration, _cwd, _cmd, _metadata = record.args
    assert _code == 3
    assert _cwd == cwd
    assert _cmd == request.shell_cmd
    assert isinstance(_duration, float)
    assert _duration > 0
    assert isinstance(_metadata, str)
    assert _metadata.startswith(" pid=")


def test_command_does_not_exist(caplog: LogCaptureFixture, os_env: dict[str, str]) -> None:
    caplog.set_level(logging.NOTSET)
    executor = LocalSubProcessExecutor(colored=False)
    request = ExecuteRequest(
        cmd=["sys-must-be-missing"],
        cwd=Path().absolute(),
        env=os_env,
        stdin=StdinSource.OFF,
        run_id="",
    )
    out_err = FakeOutErr()
    with executor.call(request, show=False, out_err=out_err.out_err, env=MagicMock()) as status:
        while status.exit_code is None:  # pragma: no branch
            status.wait()  # pragma: no cover
    outcome = status.outcome
    assert outcome is not None

    assert bool(outcome) is False, outcome
    assert outcome.exit_code != Outcome.OK
    assert not outcome.out
    assert not outcome.err
    assert not caplog.records


@pytest.mark.skipif(sys.platform == "win32", reason="You need a conhost shell for keyboard interrupt")
@pytest.mark.flaky(max_runs=3, min_passes=1)
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
        raise  # pragma: no cover

    print(f"test running in {os.getpid()} and sending CTRL+C to {process.pid}", file=sys.stderr)  # noqa: T201
    process.send_signal(SIG_INTERRUPT)
    try:
        process.communicate(timeout=3)
    except subprocess.TimeoutExpired:  # pragma: no cover
        process.kill()
        raise

    out, err = capfd.readouterr()
    assert f"W	requested interrupt of {child} from {root}, activate in 0.01" in err, err
    assert f"W	send signal SIGINT(2) to {child} from {root} with timeout 0.05" in err, err
    assert f"W	send signal SIGTERM(15) to {child} from {root} with timeout 0.07" in err, err
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
    try:
        import termios  # noqa: F401, PLC0415
    except ImportError:
        exp_tty = False  # platforms without tty support at all
    else:
        # to avoid trying (and failing) to copy mode bits
        exp_tty = tty
        mocker.patch("termios.tcgetattr")
        mocker.patch("termios.tcsetattr")

    executor = LocalSubProcessExecutor(colored=False)
    cmd: list[str] = [sys.executable, str(Path(__file__).parent / "tty_check.py")]
    request = ExecuteRequest(cmd=cmd, stdin=StdinSource.API, cwd=Path.cwd(), env=dict(os.environ), run_id="")
    out_err = FakeOutErr()
    with executor.call(request, show=False, out_err=out_err.out_err, env=MagicMock()) as status:
        while status.exit_code is None:  # pragma: no branch
            status.wait()
    outcome = status.outcome
    assert outcome is not None

    assert outcome
    info = json.loads(outcome.out)
    assert info == {
        "stdout": exp_tty,
        "stderr": exp_tty,
        "stdin": False,
        "terminal": [100, 100],
    }


@pytest.mark.parametrize("mode", ["stem", "full", "stem-pattern", "full-pattern", "all"])
def test_allow_list_external_ok(fake_exe_on_path: Path, mode: str) -> None:
    exe = f"{fake_exe_on_path}{'.EXE' if sys.platform == 'win32' else ''}"
    allow = exe if "full" in mode else fake_exe_on_path.stem
    allow = f"{allow[:-2]}*" if "pattern" in mode else allow
    allow = "*" if mode == "all" else allow

    request = ExecuteRequest(
        cmd=[fake_exe_on_path.stem],
        cwd=Path.cwd(),
        env={"PATH": os.environ["PATH"]},
        stdin=StdinSource.OFF,
        run_id="run-id",
        allow=[allow],
    )
    inst = LocalSubProcessExecuteInstance(request, MagicMock(), out=SyncWrite("out", None), err=SyncWrite("err", None))

    assert inst.cmd == [exe]


def test_shebang_limited_on(tmp_path: Path) -> None:
    exe, script, instance = _create_shebang_test(tmp_path, env={"TOX_LIMITED_SHEBANG": "1"})
    if sys.platform == "win32":  # pragma: win32 cover
        assert instance.cmd == [str(script), "--magic"]
    else:
        assert instance.cmd == [exe, "-s", str(script), "--magic"]


@pytest.mark.parametrize("env", [{}, {"TOX_LIMITED_SHEBANG": ""}])
def test_shebang_limited_off(tmp_path: Path, env: dict[str, str]) -> None:
    _, script, instance = _create_shebang_test(tmp_path, env=env)
    assert instance.cmd == [str(script), "--magic"]


def test_shebang_failed_to_parse(tmp_path: Path) -> None:
    _, script, instance = _create_shebang_test(tmp_path, env={"TOX_LIMITED_SHEBANG": "yes"})
    script.write_text("")
    assert instance.cmd == [str(script), "--magic"]


def _create_shebang_test(tmp_path: Path, env: dict[str, str]) -> tuple[str, Path, LocalSubProcessExecuteInstance]:
    exe = shutil.which("python")
    assert exe is not None
    script = tmp_path / f"s{'.EXE' if sys.platform == 'win32' else ''}"
    script.write_text(f"#!{exe} -s")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)  # mark it executable
    env["PATH"] = str(script.parent)
    request = create_autospec(ExecuteRequest, cmd=["s", "--magic"], env=env, allow=None)
    writer = create_autospec(SyncWrite)
    instance = LocalSubProcessExecuteInstance(request, create_autospec(ExecuteOptions), writer, writer)
    return exe, script, instance


@pytest.mark.parametrize("key", ["COLUMNS", "ROWS"])
def test_local_execute_does_not_overwrite(key: str, mocker: MockerFixture) -> None:
    mocker.patch("shutil.get_terminal_size", return_value=(101, 102))
    env = dict(os.environ)
    env[key] = key
    executor = LocalSubProcessExecutor(colored=False)
    cmd = [sys.executable, "-c", f"import os; print(os.environ['{key}'], end='')"]
    request = ExecuteRequest(cmd=cmd, stdin=StdinSource.API, cwd=Path.cwd(), env=env, run_id="")
    out_err = FakeOutErr()
    with executor.call(request, show=False, out_err=out_err.out_err, env=MagicMock()) as status:
        while status.exit_code is None:  # pragma: no branch
            status.wait()
    outcome = status.outcome

    assert outcome is not None
    assert outcome.out == key
