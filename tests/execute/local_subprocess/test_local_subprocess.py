from __future__ import annotations

import contextlib
import errno
import json
import locale
import logging
import os
import re
import selectors
import stat
import subprocess
import sys
import time
from io import TextIOWrapper
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Final, NamedTuple, NoReturn

import psutil
import pytest
from colorama import Fore
from psutil import AccessDenied

from tox.config.sets import EnvConfigSet
from tox.execute.api import ExecuteOptions, FinishedExecuteStatus, Outcome
from tox.execute.local_sub_process import (
    SIG_INTERRUPT,
    LocalSubProcessExecuteInstance,
    LocalSubProcessExecutor,
    execute,
    read_via_thread_windows,
)
from tox.execute.local_sub_process.read_via_thread_unix import ReadViaThreadUnix
from tox.execute.request import ExecuteRequest, StdinSource
from tox.execute.stream import SyncWrite
from tox.report import NamedBytesIO
from tox.tox_env.api import ToxEnv

if TYPE_CHECKING:
    from pytest_mock import MockerFixture, MockType

    from tox.pytest import CaptureFixture, LogCaptureFixture, MonkeyPatch, ToxProjectCreator

_EXE_SUFFIX: Final[str] = ".EXE" if sys.platform == "win32" else ""


@pytest.mark.parametrize(("out", "err"), [pytest.param("out", "err", id="simple"), pytest.param("", "", id="nothing")])
def test_local_execute_basic_pass_hidden(
    caplog: LogCaptureFixture, os_env: dict[str, str], out: str, err: str, mocker: MockerFixture
) -> None:
    out_got, err_got = _run_basic_pass(
        caplog, os_env, out, err, show=False, color=False, stderr_color="RED", mocker=mocker
    ).read_out_err()
    assert not out_got
    assert not err_got


def _run_basic_pass(
    caplog: LogCaptureFixture,
    os_env: dict[str, str],
    out: str,
    err: str,
    *,
    show: bool,
    color: bool,
    stderr_color: str,
    mocker: MockerFixture,
) -> FakeOutErr:
    caplog.set_level(logging.NOTSET)
    executor = LocalSubProcessExecutor(colored=color)

    tox_env = _create_mock_env(mocker, stderr_color)

    code = f"import sys; print({out!r}, end=''); print({err!r}, end='', file=sys.stderr)"
    request = ExecuteRequest(cmd=[sys.executable, "-c", code], cwd=Path(), env=os_env, stdin=StdinSource.OFF, run_id="")
    out_err = FakeOutErr()

    with executor.call(request, show=show, out_err=out_err.out_err, env=tox_env) as status:
        while status.exit_code is None:  # pragma: no branch  # other outcome untested
            status.wait()
    assert (status.out, status.err) == (out.encode(), err.encode())
    outcome = status.outcome
    assert outcome is not None
    assert bool(outcome) is True, outcome
    assert (outcome.exit_code, outcome.err, outcome.out, outcome.request) == (Outcome.OK, err, out, request)
    assert not caplog.records
    return out_err


def _create_mock_env(mocker: MockerFixture, stderr_color: str | None = None) -> ToxEnv:
    # Create a mock tox environment with no_capture=False to prevent console inheritance.
    return mocker.create_autospec(
        ToxEnv,
        instance=True,
        conf=mocker.create_autospec(EnvConfigSet, instance=True),
        options=SimpleNamespace(no_capture=False, stderr_color=stderr_color),
    )


class FakeOutErr:
    def __init__(self) -> None:
        self.out_err = (
            TextIOWrapper(NamedBytesIO("out"), encoding=locale.getpreferredencoding(False)),
            TextIOWrapper(NamedBytesIO("err"), encoding=locale.getpreferredencoding(False)),
        )

    def read_out_err(self) -> tuple[str, str]:
        out_got = self.out_err[0].buffer.getvalue().decode(self.out_err[0].encoding)
        return out_got, self.out_err[1].buffer.getvalue().decode(self.out_err[1].encoding)


@pytest.mark.parametrize(("out", "err"), [pytest.param("out", "err", id="simple"), pytest.param("", "", id="nothing")])
def test_local_execute_basic_pass_shown(
    caplog: LogCaptureFixture, os_env: dict[str, str], out: str, err: str, mocker: MockerFixture
) -> None:
    out_got, err_got = _run_basic_pass(
        caplog, os_env, out, err, show=True, color=False, stderr_color="RED", mocker=mocker
    ).read_out_err()
    assert out_got == out
    assert err_got == err


@pytest.mark.parametrize(
    "stderr_color",
    [
        pytest.param("RED", id="stderr_color_default"),
        pytest.param("YELLOW", id="stderr_color_yellow"),
        pytest.param("RESET", id="stderr_color_reset"),
    ],
)
def test_local_execute_basic_pass_shown_colored(
    caplog: LogCaptureFixture, os_env: dict[str, str], stderr_color: str, mocker: MockerFixture
) -> None:
    out_got, err_got = _run_basic_pass(
        caplog, os_env, "out", "err", show=True, color=True, stderr_color=stderr_color, mocker=mocker
    ).read_out_err()
    assert out_got == "out"
    assert err_got == f"{getattr(Fore, stderr_color)}err{Fore.RESET}"


def test_local_execute_basic_pass_shown_colored_empty_err(
    caplog: LogCaptureFixture, os_env: dict[str, str], mocker: MockerFixture
) -> None:
    out_got, err_got = _run_basic_pass(
        caplog, os_env, "", "", show=True, color=True, stderr_color="RED", mocker=mocker
    ).read_out_err()
    assert not out_got
    assert not err_got


@pytest.mark.parametrize(
    ("no_capture", "stdin", "capture", "expected"),
    [
        pytest.param(False, StdinSource.API, False, (b"out", b"err", "", ""), id="capture-api"),
        pytest.param(False, StdinSource.USER, False, (b"out", b"err", "", ""), id="capture-user"),
        pytest.param(False, StdinSource.OFF, False, (b"out", b"err", "", ""), id="capture-off"),
        pytest.param(True, StdinSource.API, False, (b"out", b"err", "", ""), id="no-capture-api"),
        pytest.param(True, StdinSource.USER, False, (b"", b"", "out", "err"), id="no-capture-user"),
        pytest.param(True, StdinSource.OFF, False, (b"", b"", "out", "err"), id="no-capture-off"),
        pytest.param(True, StdinSource.API, True, (b"out", b"err", "", ""), id="required-capture-api"),
        pytest.param(True, StdinSource.USER, True, (b"out", b"err", "", ""), id="required-capture-user"),
        pytest.param(True, StdinSource.OFF, True, (b"out", b"err", "", ""), id="required-capture-off"),
    ],
)
def test_local_execute_capture(
    tox_project: ToxProjectCreator,
    os_env: dict[str, str],
    capfd: CaptureFixture,
    no_capture: bool,
    stdin: StdinSource,
    capture: bool,
    expected: tuple[bytes, bytes, str, str],
) -> None:
    tox_env: Final[ToxEnv] = tox_project({"tox.ini": ""}).run("l").state.envs["py"]
    tox_env.options.no_capture = no_capture
    code: Final[str] = "import sys; print('out', end=''); print('err', end='', file=sys.stderr)"
    request: Final[ExecuteRequest] = ExecuteRequest(
        cmd=[sys.executable, "-c", code], cwd=Path(), env=os_env, stdin=stdin, run_id="", capture=capture
    )
    with LocalSubProcessExecutor(colored=False).build_instance(
        request, ExecuteOptions(tox_env), SyncWrite("out", None), SyncWrite("err", None)
    ) as status:
        status.wait()
    assert (status.out, status.err, *capfd.readouterr()) == expected


def test_local_execute_basic_pass_show_on_standard_newline_flush(
    caplog: LogCaptureFixture, mocker: MockerFixture
) -> None:
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
    with executor.call(request, show=True, out_err=out_err.out_err, env=_create_mock_env(mocker)) as status:
        while status.exit_code is None:  # pragma: no branch  # other outcome untested
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


def test_local_execute_start_error_masks_secret_flag(
    caplog: LogCaptureFixture, os_env: dict[str, str], mocker: MockerFixture
) -> None:
    request: Final = ExecuteRequest(
        cmd=["--token=hunter2"], cwd=Path.cwd(), env=os_env, stdin=StdinSource.OFF, run_id=""
    )
    with LocalSubProcessExecutor(colored=False).call(
        request, show=True, out_err=FakeOutErr().out_err, env=_create_mock_env(mocker)
    ) as status:
        status.wait()
    assert isinstance(status.start_error, OSError)
    assert "Exception running subprocess" in caplog.text
    assert "--token=*******" in caplog.text or "--token" not in caplog.text
    assert "hunter2" not in caplog.text


def test_local_execute_write_a_lot(os_env: dict[str, str], mocker: MockerFixture) -> None:
    executor = LocalSubProcessExecutor(colored=False)
    count = 10_000
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
    with executor.call(request, show=False, out_err=FakeOutErr().out_err, env=_create_mock_env(mocker)) as status:
        while status.exit_code is None:  # pragma: no branch  # other outcome untested
            status.wait()
    outcome = status.outcome
    assert outcome is not None
    assert bool(outcome), outcome
    expected_out = f"{'o' * count}{os.linesep}{'b' * count}{os.linesep}"
    assert outcome.out == expected_out, expected_out[len(outcome.out) :]
    expected_err = f"{'e' * count}{os.linesep}{'a' * count}{os.linesep}"
    assert outcome.err == expected_err, expected_err[len(outcome.err) :]


@pytest.mark.skipif(sys.platform == "win32", reason="Unix terminal size test")
def test_local_execute_terminal_size(os_env: dict[str, str], monkeypatch: MonkeyPatch, mocker: MockerFixture) -> None:
    # Regression test for #2999 - check terminal size is set correctly in tox subprocess.
    import pty  # ruff:ignore[import-outside-top-level]

    terminal_size = os.terminal_size((84, 42))
    main, child = pty.openpty()  # Unix-only

    # Use ReadViaThreadUnix to help with debugging the test itself.
    pipe_out = ReadViaThreadUnix(main, sys.stdout.buffer.write, name="testout", drain=True)
    with (
        pipe_out,
        monkeypatch.context() as monkey,
        open(  # ruff:ignore[builtin-open]  # reads what subprocess wrote
            child, "w", encoding=locale.getpreferredencoding(False)
        ) as stdout_mock,
    ):
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
        with executor.call(request, show=False, out_err=FakeOutErr().out_err, env=_create_mock_env(mocker)) as status:
            while status.exit_code is None:  # pragma: no branch  # other outcome untested
                status.wait()
    outcome = status.outcome
    assert outcome is not None
    assert bool(outcome), outcome
    expected_out = f"{terminal_size!r}\r\n"
    assert outcome.out == expected_out, expected_out[len(outcome.out) :]
    assert not outcome.err


def test_local_execute_basic_fail(
    capsys: CaptureFixture, caplog: LogCaptureFixture, monkeypatch: MonkeyPatch, mocker: MockerFixture
) -> None:
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
    with executor.call(request, show=False, out_err=out_err.out_err, env=_create_mock_env(mocker)) as status:
        while status.exit_code is None:  # pragma: no branch  # other outcome untested
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
    assert (outcome.exit_code, outcome.err, outcome.out, outcome.request) == (3, "err", "out", request)

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
    assert (record.levelno, record.msg) == (logging.CRITICAL, "exit %s (%.2f seconds) %s> %s%s")
    assert record.args is not None
    code, duration, cwd_, cmd_, metadata = record.args
    assert code == 3
    assert cwd_ == cwd
    assert cmd_ == request.shell_cmd
    assert isinstance(duration, float)
    assert duration > 0
    assert isinstance(metadata, str)
    assert metadata.startswith(" pid=")


def test_command_does_not_exist(caplog: LogCaptureFixture, os_env: dict[str, str], mocker: MockerFixture) -> None:
    caplog.set_level(logging.NOTSET)
    executor = LocalSubProcessExecutor(colored=False)
    request = ExecuteRequest(
        cmd=["sys-must-be-missing"],
        cwd=Path().absolute(),
        env=os_env,
        stdin=StdinSource.OFF,
        run_id="",
    )
    with executor.call(request, show=False, out_err=FakeOutErr().out_err, env=_create_mock_env(mocker)) as status:
        while status.exit_code is None:  # pragma: no branch  # other outcome untested
            status.wait()  # pragma: no cover  # setup not built by tests
    outcome = status.outcome
    assert outcome is not None

    assert bool(outcome) is False, outcome
    assert outcome.exit_code != Outcome.OK
    assert not outcome.out
    assert not outcome.err
    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "ERROR"
    assert re.match(
        r".*(No such file or directory|The system cannot find the file specified).*", caplog.records[0].message
    )


@pytest.fixture(
    params=[
        pytest.param(0, id="success"),
        pytest.param(-2, id="interrupted"),
        pytest.param(None, id="not-started"),
    ]
)
def finished_exit_code(request: pytest.FixtureRequest) -> int | None:
    return request.param


@pytest.fixture
def finished_status(finished_exit_code: int | None, mocker: MockerFixture) -> FinishedExecuteStatus:
    return FinishedExecuteStatus(
        mocker.create_autospec(ExecuteOptions), SyncWrite("out", None), SyncWrite("err", None), finished_exit_code
    )


def test_finished_status_exit_code(finished_status: FinishedExecuteStatus, finished_exit_code: int | None) -> None:
    assert finished_status.exit_code == finished_exit_code


def test_finished_status_wait_returns_exit_code(
    finished_status: FinishedExecuteStatus, finished_exit_code: int | None
) -> None:
    assert finished_status.wait(0.5) == finished_exit_code


def test_finished_status_interrupt_keeps_exit_code(
    finished_status: FinishedExecuteStatus, finished_exit_code: int | None
) -> None:
    finished_status.interrupt()
    assert finished_status.exit_code == finished_exit_code


def test_finished_status_write_stdin_discards_content(finished_status: FinishedExecuteStatus) -> None:
    finished_status.write_stdin("content")
    assert (finished_status.out, finished_status.err) == (bytearray(), bytearray())


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
        pytest.skip(str(exc))  # pragma: no cover  # setup not built by tests
        raise  # pragma: no cover  # untested error path

    print(  # ruff:ignore[print]  # test output
        f"test running in {os.getpid()} and sending CTRL+C to {process.pid}", file=sys.stderr
    )
    process.send_signal(SIG_INTERRUPT)
    try:
        process.communicate(timeout=3)
    except subprocess.TimeoutExpired:  # pragma: no cover  # untested error path
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


@pytest.mark.skipif(sys.platform == "win32", reason="pty is Unix-only")
def test_pty_closes_fds_when_termios_fails(mocker: MockerFixture) -> None:
    # If terminal attributes cannot be inherited, the freshly opened pty fds must be released.
    termios = pytest.importorskip("termios")
    pty = pytest.importorskip("pty")
    mocker.patch("sys.stdout.isatty", autospec=True, return_value=True)
    mocker.patch.object(termios, "tcgetattr", autospec=True, side_effect=termios.error)
    openpty_spy = mocker.spy(pty, "openpty")
    close_spy = mocker.spy(os, "close")

    result = execute._pty("stdout")  # ruff:ignore[private-member-access]  # injects termios failure

    assert result is None
    main, child = openpty_spy.spy_return
    assert {call.args[0] for call in close_spy.call_args_list} == {main, child}


@pytest.mark.skipif(sys.platform == "win32", reason="pty is Unix-only")
def test_local_subprocess_tty_closes_master_fd(monkeypatch: MonkeyPatch, mocker: MockerFixture) -> None:
    # The pty master fd is not a process stream, so it must be closed explicitly and not leaked.
    pytest.importorskip("termios")
    monkeypatch.setenv("COLUMNS", "100")
    monkeypatch.setenv("LINES", "100")
    mocker.patch("sys.stdout.isatty", autospec=True, return_value=True)
    mocker.patch("sys.stderr.isatty", autospec=True, return_value=True)
    mocker.patch("termios.tcgetattr", autospec=True)
    mocker.patch("termios.tcsetattr", autospec=True)
    pty_spy = mocker.spy(execute, "_pty")

    executor = LocalSubProcessExecutor(colored=False)
    cmd = [sys.executable, str(Path(__file__).parent / "tty_check.py")]
    request = ExecuteRequest(cmd=cmd, stdin=StdinSource.API, cwd=Path.cwd(), env=dict(os.environ), run_id="")
    with executor.call(request, show=False, out_err=FakeOutErr().out_err, env=_create_mock_env(mocker)) as status:
        while status.exit_code is None:  # pragma: no branch  # other outcome untested
            status.wait()

    master_fds = [result[0] for result in pty_spy.spy_return_list]
    assert len(master_fds) == 2  # tty path taken for stdout and stderr
    for fd in master_fds:
        with pytest.raises(OSError, match="Bad file descriptor"):
            os.fstat(fd)


@pytest.mark.skipif(sys.platform == "win32", reason="pty is Unix-only")
def test_get_stream_file_no_closes_each_pty_fd_once(mocker: MockerFixture) -> None:
    # Each pty fd must be closed exactly once.
    #
    # The child fd is closed once the child has inherited it; closing it a second time on generator teardown can race a
    # parallel run that has reused the freed fd number, corrupting the sibling's fd (see #3975).
    main_fd, child_fd = 11, 22
    mocker.patch.object(execute, "_pty", autospec=True, return_value=(main_fd, child_fd))
    close_spy = mocker.patch.object(os, "close", autospec=True)

    gen = LocalSubProcessExecuteInstance.get_stream_file_no("stdout")
    assert next(gen) == child_fd
    assert gen.send(mocker.create_autospec(subprocess.Popen, instance=True)) == main_fd
    gen.close()

    closed = [call.args[0] for call in close_spy.call_args_list]
    assert closed.count(child_fd) == 1
    assert closed.count(main_fd) == 1


@pytest.mark.skipif(sys.platform != "win32", reason="overlapped I/O reader is Windows-only")
def test_read_via_thread_windows_stops_while_read_pending(mocker: MockerFixture) -> None:
    # A never-completing overlapped read must not keep the reader thread alive after stop is set.
    pending = OSError()
    pending.winerror = read_via_thread_windows.ERROR_IO_INCOMPLETE
    overlapped = mocker.create_autospec(read_via_thread_windows._overlapped.Overlapped, instance=True)  # ruff:ignore[private-member-access]  # the module under test binds it
    overlapped.getresult.side_effect = pending  # the read never completes
    overlapped_module = mocker.create_autospec(read_via_thread_windows._overlapped)  # ruff:ignore[private-member-access]  # the module under test binds it
    overlapped_module.Overlapped.return_value = overlapped
    mocker.patch.object(read_via_thread_windows, "_overlapped", overlapped_module)

    reader = read_via_thread_windows.ReadViaThreadWindows(
        file_no=0, handler=lambda _chunk: 0, name="pending", drain=False
    )
    reader.thread.start()
    deadline = time.monotonic() + 5
    while not overlapped.getresult.called and time.monotonic() < deadline:
        time.sleep(0.01)  # simplint: ignore[SMP808]  # polls a mock the reader calls; nothing to wait on
    reader.stop.set()
    reader.thread.join(timeout=5)

    assert not reader.thread.is_alive()


@pytest.mark.parametrize("tty_mode", [pytest.param("on", id="on"), pytest.param("off", id="off")])
def test_local_subprocess_tty(monkeypatch: MonkeyPatch, mocker: MockerFixture, tty_mode: str) -> None:
    monkeypatch.setenv("COLUMNS", "100")
    monkeypatch.setenv("LINES", "100")
    tty = tty_mode == "on"
    mocker.patch("sys.stdout.isatty", autospec=True, return_value=tty)
    mocker.patch("sys.stderr.isatty", autospec=True, return_value=tty)
    try:
        import termios  # ruff:ignore[unused-import, import-outside-top-level]  # re-exported and deferred import
    except ImportError:
        exp_tty = False  # platforms without tty support at all
    else:
        # to avoid trying (and failing) to copy mode bits
        exp_tty = tty
        mocker.patch("termios.tcgetattr", autospec=True)
        mocker.patch("termios.tcsetattr", autospec=True)

    executor = LocalSubProcessExecutor(colored=False)
    cmd: list[str] = [sys.executable, str(Path(__file__).parent / "tty_check.py")]
    request = ExecuteRequest(cmd=cmd, stdin=StdinSource.API, cwd=Path.cwd(), env=dict(os.environ), run_id="")
    with executor.call(request, show=False, out_err=FakeOutErr().out_err, env=_create_mock_env(mocker)) as status:
        while status.exit_code is None:  # pragma: no branch  # other outcome untested
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


@pytest.mark.parametrize(
    "mode",
    [
        pytest.param("stem", id="stem"),
        pytest.param("full", id="full"),
        pytest.param("stem-pattern", id="stem-dash-pattern"),
        pytest.param("full-pattern", id="full-dash-pattern"),
        pytest.param("all", id="all"),
    ],
)
def test_allow_list_external_ok(fake_exe_on_path: Path, mode: str, mocker: MockerFixture) -> None:
    exe = f"{fake_exe_on_path}{_EXE_SUFFIX}"
    allow = {
        "stem": fake_exe_on_path.stem,
        "full": exe,
        "stem-pattern": f"{fake_exe_on_path.stem[:-2]}*",
        "full-pattern": f"{exe[:-2]}*",
        "all": "*",
    }[mode]

    request = ExecuteRequest(
        cmd=[fake_exe_on_path.stem],
        cwd=Path.cwd(),
        env={"PATH": os.environ["PATH"]},
        stdin=StdinSource.OFF,
        run_id="run-id",
        allow=[allow],
    )
    inst = LocalSubProcessExecuteInstance(
        request, ExecuteOptions(_create_mock_env(mocker)), out=SyncWrite("out", None), err=SyncWrite("err", None)
    )

    assert inst.cmd == [exe]


@pytest.mark.skipif(sys.platform == "win32", reason="posix shebang handling")
def test_shebang_limited_on_posix(tmp_path: Path, mocker: MockerFixture) -> None:
    exe, script, instance = _create_shebang_test(tmp_path, env={"TOX_LIMITED_SHEBANG": "1"}, mocker=mocker)
    assert instance.cmd == [exe, "-s", str(script), "--magic"]


def _create_shebang_test(tmp_path: Path, env: dict[str, str], mocker: MockerFixture) -> _ShebangTest:
    exe: Final[str] = sys.executable
    script = tmp_path / f"s{_EXE_SUFFIX}"
    script.write_text(f"#!{exe} -s")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)  # mark it executable
    env["PATH"] = str(script.parent)
    request = mocker.create_autospec(ExecuteRequest, cmd=["s", "--magic"], cwd=tmp_path, env=env, allow=None)
    writer = mocker.create_autospec(SyncWrite)
    return _ShebangTest(
        exe, script, LocalSubProcessExecuteInstance(request, mocker.create_autospec(ExecuteOptions), writer, writer)
    )


class _ShebangTest(NamedTuple):
    exe: str
    script: Path
    instance: LocalSubProcessExecuteInstance


@pytest.mark.skipif(sys.platform != "win32", reason="windows shebang handling")
def test_shebang_limited_on_windows(tmp_path: Path, mocker: MockerFixture) -> None:
    _exe, script, instance = _create_shebang_test(tmp_path, env={"TOX_LIMITED_SHEBANG": "1"}, mocker=mocker)
    assert instance.cmd == [str(script), "--magic"]


@pytest.mark.parametrize(
    "env",
    [
        pytest.param({}, id="open-close"),
        pytest.param(
            {"TOX_LIMITED_SHEBANG": ""},
            id="open-quote-tox-underscore-limited-underscore-shebang-quote-colon-space-quote-quote-close",
        ),
    ],
)
def test_shebang_limited_off(tmp_path: Path, env: dict[str, str], mocker: MockerFixture) -> None:
    _, script, instance = _create_shebang_test(tmp_path, env=env, mocker=mocker)
    assert instance.cmd == [str(script), "--magic"]


def test_shebang_failed_to_parse(tmp_path: Path, mocker: MockerFixture) -> None:
    _, script, instance = _create_shebang_test(tmp_path, env={"TOX_LIMITED_SHEBANG": "yes"}, mocker=mocker)
    script.write_text("")
    assert instance.cmd == [str(script), "--magic"]


@pytest.mark.parametrize("name", [pytest.param("build.cmd", id="cmd"), pytest.param("build.BAT", id="bat-uppercase")])
def test_windows_batch_file_started_via_cmd_exe(
    tmp_path: Path, mocker: MockerFixture, monkeypatch: MonkeyPatch, name: str
) -> None:
    mocker.patch.object(execute, "sys", mocker.create_autospec(sys, platform="win32"))
    popen: Final[MockType] = mocker.patch.object(
        execute, "Popen", autospec=True, side_effect=OSError(errno.ENOENT, "not started")
    )
    monkeypatch.setenv("SYSTEMROOT", str(tmp_path))
    script: Final[Path] = tmp_path / name
    script.touch()
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    request: Final[ExecuteRequest] = ExecuteRequest(
        cmd=[str(script), "v1.0&next"], cwd=tmp_path, env={"PATH": ""}, stdin=StdinSource.OFF, run_id=""
    )
    writer: Final[SyncWrite] = SyncWrite("out", None)

    with LocalSubProcessExecuteInstance(request, ExecuteOptions(_create_mock_env(mocker)), writer, writer) as status:
        assert status.exit_code == errno.ENOENT

    assert (popen.call_args.args, popen.call_args.kwargs["executable"]) == (
        (f'cmd.exe /e:ON /v:OFF /d /c ""{script}" "v1.0&next""',),
        str(tmp_path / "System32" / "cmd.exe"),
    )


@pytest.mark.skipif(sys.platform != "win32", reason="batch files are Windows-only")
@pytest.mark.parametrize(
    "name",
    [
        pytest.param("show args.cmd", id="space"),
        pytest.param("show & args.cmd", id="operator"),
        pytest.param("show %PATH% args.cmd", id="variable"),
    ],
)
def test_windows_batch_file_args_are_literal(
    tmp_path: Path, os_env: dict[str, str], name: str, mocker: MockerFixture
) -> None:
    script: Final[Path] = tmp_path / name
    script.write_text(f'@"{sys.executable}" -c "import json, sys; print(json.dumps(sys.argv[1:]))" %*\n')
    args: Final[list[str]] = [
        "v1.0",
        "v1.0&next",
        'a b" & next & "',
        '\\"|next',
        "%PATH%",
        "!PATH!",
        "^",
        "a=b",
        "a\\",
        "",
    ]
    request: Final[ExecuteRequest] = ExecuteRequest(
        cmd=[str(script), *args], cwd=tmp_path, env=os_env, stdin=StdinSource.OFF, run_id=""
    )
    executor: Final[LocalSubProcessExecutor] = LocalSubProcessExecutor(colored=False)

    with executor.call(request, show=False, out_err=FakeOutErr().out_err, env=_create_mock_env(mocker)) as status:
        status.wait()

    assert status.outcome is not None
    assert json.loads(status.outcome.out) == args


@pytest.mark.skipif(sys.platform == "win32", reason="only POSIX resolves relative commands from the child's cwd")
@pytest.mark.parametrize(
    ("cmd", "path"),
    [
        pytest.param("scripts/s", os.defpath, id="relative-command"),
        pytest.param("s", "scripts", id="relative-path-entry"),
    ],
)
def test_shebang_resolved_from_request_cwd(
    tmp_path: Path, monkeypatch: MonkeyPatch, cmd: str, path: str, mocker: MockerFixture
) -> None:
    for folder, interpreter in (("project", "/bin/sh"), ("invoked_from", "/bin/other")):
        script = tmp_path / folder / "scripts" / "s"
        script.parent.mkdir(parents=True)
        script.write_text(f"#!{interpreter}")
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
    monkeypatch.chdir(tmp_path / "invoked_from")
    request: Final = ExecuteRequest(
        cmd=[cmd, "--magic"],
        cwd=tmp_path / "project",
        env={"PATH": path, "TOX_LIMITED_SHEBANG": "1"},
        stdin=StdinSource.OFF,
        run_id="run-id",
        allow=[cmd],
    )
    writer: Final = mocker.create_autospec(SyncWrite)
    instance: Final = LocalSubProcessExecuteInstance(request, mocker.create_autospec(ExecuteOptions), writer, writer)

    assert instance.cmd == ["/bin/sh", str(tmp_path / "project" / "scripts" / "s"), "--magic"]


@pytest.mark.parametrize("key", [pytest.param("COLUMNS", id="columns"), pytest.param("ROWS", id="rows")])
def test_local_execute_does_not_overwrite(key: str, mocker: MockerFixture) -> None:
    mocker.patch("shutil.get_terminal_size", autospec=True, return_value=(101, 102))
    env = dict(os.environ)
    env[key] = key
    executor = LocalSubProcessExecutor(colored=False)
    cmd = [sys.executable, "-c", f"import os; print(os.environ['{key}'], end='')"]
    request = ExecuteRequest(cmd=cmd, stdin=StdinSource.API, cwd=Path.cwd(), env=env, run_id="")
    with executor.call(request, show=False, out_err=FakeOutErr().out_err, env=_create_mock_env(mocker)) as status:
        while status.exit_code is None:  # pragma: no branch  # other outcome untested
            status.wait()
    outcome = status.outcome

    assert outcome is not None
    assert outcome.out == key


@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific tests")
def test_read_via_thread_eintr_during_select(mocker: MockerFixture) -> None:
    # Test that EINTR during selector.select() is handled correctly.
    # Create a pipe
    data_received: list[bytes] = []
    eintr_raised = [False]

    def handler(data: bytes) -> int:
        data_received.append(data)
        return len(data)

    original_select = selectors.DefaultSelector.select

    def mock_select(
        self: selectors.DefaultSelector, timeout: float | None = None
    ) -> list[tuple[selectors.SelectorKey, int]]:
        if not eintr_raised[0]:
            eintr_raised[0] = True
            err = OSError("Interrupted system call")
            err.errno = errno.EINTR
            raise err
        return original_select(self, timeout)

    mocker.patch.object(selectors.DefaultSelector, "select", mock_select)
    read_fd, write_fd = os.pipe()
    try:
        os.write(write_fd, b"test data")
        os.close(write_fd)
        reader = ReadViaThreadUnix(read_fd, handler, "test", drain=True)
        with reader:
            reader.thread.join(timeout=2)
    finally:
        with contextlib.suppress(OSError):
            os.close(read_fd)
    assert eintr_raised[0], "EINTR should have been raised"
    assert b"test data" in data_received, "Data should still be read after EINTR"


@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific tests")
def test_read_via_thread_eintr_during_read(mocker: MockerFixture) -> None:
    # Test that EINTR during os.read() is handled correctly.
    data_received: list[bytes] = []
    original_read = os.read
    call_count = [0]

    def handler(data: bytes) -> int:
        data_received.append(data)
        return len(data)

    def mock_read(fd: int, size: int) -> bytes:
        call_count[0] += 1
        if call_count[0] == 1:
            err = OSError("Interrupted")
            err.errno = errno.EINTR
            raise err
        return original_read(fd, size)

    mocker.patch("os.read", mock_read)
    read_fd, write_fd = os.pipe()
    try:
        os.write(write_fd, b"test data")
        os.close(write_fd)
        reader = ReadViaThreadUnix(read_fd, handler, "test", drain=True)
        with reader:
            reader.thread.join(timeout=1)
    finally:
        with contextlib.suppress(OSError):
            os.close(read_fd)
    assert b"test data" in data_received


@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific tests")
def test_read_via_thread_ebadf_during_read(mocker: MockerFixture) -> None:
    # Test that EBADF during os.read() is handled correctly.
    data_received: list[bytes] = []

    def handler(data: bytes) -> int:
        data_received.append(data)
        return len(data)

    def mock_read(fd: int, size: int) -> NoReturn:  # ruff:ignore[unused-function-argument]  # interface signature
        err = OSError("Bad file descriptor")
        err.errno = errno.EBADF
        raise err

    mocker.patch("os.read", mock_read)
    read_fd, write_fd = os.pipe()
    try:
        # Close write end
        os.close(write_fd)
        reader = ReadViaThreadUnix(read_fd, handler, "test", drain=True)
        with reader:
            reader.thread.join(timeout=1)
        # Should not crash, but won't receive data due to EBADF
    finally:
        with contextlib.suppress(OSError):
            os.close(read_fd)


@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific tests")
def test_read_via_thread_drain_no_data() -> None:
    # Test drain_stream when there's no data ready.
    data_received: list[bytes] = []

    def handler(data: bytes) -> int:
        data_received.append(data)
        return len(data)

    read_fd, write_fd = os.pipe()
    try:
        os.close(write_fd)
        ReadViaThreadUnix(  # ruff:ignore[private-member-access]  # closed pipe drain
            read_fd, handler, "test", drain=True
        )._drain_stream()
    finally:
        with contextlib.suppress(OSError):
            os.close(read_fd)
    assert len(data_received) == 0
