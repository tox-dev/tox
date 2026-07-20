from __future__ import annotations

import contextlib
import errno
import json
import locale
import logging
import os
import re
import selectors
import shutil
import stat
import subprocess
import sys
import time
from io import TextIOWrapper
from pathlib import Path
from typing import TYPE_CHECKING, Any, NoReturn
from unittest.mock import MagicMock, create_autospec

import psutil
import pytest
from colorama import Fore
from psutil import AccessDenied

from tox.execute import local_sub_process
from tox.execute.api import ExecuteOptions, Outcome
from tox.execute.local_sub_process import (
    SIG_INTERRUPT,
    LocalSubProcessExecuteInstance,
    LocalSubProcessExecutor,
    read_via_thread_windows,
)
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
        out_got = self.out_err[0].buffer.getvalue().decode(self.out_err[0].encoding)
        err_got = self.out_err[1].buffer.getvalue().decode(self.out_err[1].encoding)
        return out_got, err_got


def _create_mock_env() -> MagicMock:
    """Create a mock tox environment with no_capture=False to prevent console inheritance."""
    mock_env = MagicMock()
    mock_env.options.no_capture = False
    return mock_env


@pytest.mark.parametrize("color", [True, False], ids=["color", "no_color"])
@pytest.mark.parametrize(("out", "err"), [("out", "err"), ("", "")], ids=["simple", "nothing"])
@pytest.mark.parametrize("show", [True, False], ids=["show", "no_show"])
@pytest.mark.parametrize(
    "stderr_color",
    ["RED", "YELLOW", "RESET"],
    ids=["stderr_color_default", "stderr_color_yellow", "stderr_color_reset"],
)
def test_local_execute_basic_pass(
    caplog: LogCaptureFixture,
    os_env: dict[str, str],
    out: str,
    err: str,
    show: bool,
    color: bool,
    stderr_color: str,
) -> None:
    caplog.set_level(logging.NOTSET)
    executor = LocalSubProcessExecutor(colored=color)

    tox_env = _create_mock_env()
    tox_env.conf._conf.options.stderr_color = stderr_color  # ruff:ignore[private-member-access]
    code = f"import sys; print({out!r}, end=''); print({err!r}, end='', file=sys.stderr)"
    request = ExecuteRequest(cmd=[sys.executable, "-c", code], cwd=Path(), env=os_env, stdin=StdinSource.OFF, run_id="")
    out_err = FakeOutErr()

    with executor.call(request, show=show, out_err=out_err.out_err, env=tox_env) as status:
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
        expected = f"{getattr(Fore, stderr_color)}{err}{Fore.RESET}" if color and err else err
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
    with executor.call(request, show=True, out_err=out_err.out_err, env=_create_mock_env()) as status:
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
    with executor.call(request, show=False, out_err=out_err.out_err, env=_create_mock_env()) as status:
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
    import pty  # ruff:ignore[import-outside-top-level]

    terminal_size = os.terminal_size((84, 42))
    main, child = pty.openpty()  # Unix-only

    # Use ReadViaThreadUnix to help with debugging the test itself.
    pipe_out = ReadViaThreadUnix(main, sys.stdout.buffer.write, name="testout", drain=True)
    with (
        pipe_out,
        monkeypatch.context() as monkey,
        open(  # ruff:ignore[builtin-open]
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
        out_err = FakeOutErr()
        with executor.call(request, show=False, out_err=out_err.out_err, env=_create_mock_env()) as status:
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
    with executor.call(request, show=False, out_err=out_err.out_err, env=_create_mock_env()) as status:
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
    code, duration, cwd_, cmd_, metadata = record.args
    assert code == 3
    assert cwd_ == cwd
    assert cmd_ == request.shell_cmd
    assert isinstance(duration, float)
    assert duration > 0
    assert isinstance(metadata, str)
    assert metadata.startswith(" pid=")


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
    with executor.call(request, show=False, out_err=out_err.out_err, env=_create_mock_env()) as status:
        while status.exit_code is None:  # pragma: no branch
            status.wait()  # pragma: no cover
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

    print(f"test running in {os.getpid()} and sending CTRL+C to {process.pid}", file=sys.stderr)  # ruff:ignore[print]
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


@pytest.mark.skipif(sys.platform == "win32", reason="pty is Unix-only")
def test_pty_closes_fds_when_termios_fails(mocker: MockerFixture) -> None:
    """If terminal attributes cannot be inherited, the freshly opened pty fds must be released."""
    termios = pytest.importorskip("termios")
    pty = pytest.importorskip("pty")
    mocker.patch("sys.stdout.isatty", return_value=True)
    mocker.patch.object(termios, "tcgetattr", side_effect=termios.error)
    openpty_spy = mocker.spy(pty, "openpty")
    close_spy = mocker.spy(os, "close")

    result = local_sub_process._pty("stdout")  # ruff:ignore[private-member-access]

    assert result is None
    main, child = openpty_spy.spy_return
    assert {call.args[0] for call in close_spy.call_args_list} == {main, child}


@pytest.mark.skipif(sys.platform == "win32", reason="pty is Unix-only")
def test_local_subprocess_tty_closes_master_fd(monkeypatch: MonkeyPatch, mocker: MockerFixture) -> None:
    """The pty master fd is not a process stream, so it must be closed explicitly and not leaked."""
    pytest.importorskip("termios")
    monkeypatch.setenv("COLUMNS", "100")
    monkeypatch.setenv("LINES", "100")
    mocker.patch("sys.stdout.isatty", return_value=True)
    mocker.patch("sys.stderr.isatty", return_value=True)
    mocker.patch("termios.tcgetattr")
    mocker.patch("termios.tcsetattr")
    pty_spy = mocker.spy(local_sub_process, "_pty")

    executor = LocalSubProcessExecutor(colored=False)
    cmd = [sys.executable, str(Path(__file__).parent / "tty_check.py")]
    request = ExecuteRequest(cmd=cmd, stdin=StdinSource.API, cwd=Path.cwd(), env=dict(os.environ), run_id="")
    out_err = FakeOutErr()
    with executor.call(request, show=False, out_err=out_err.out_err, env=_create_mock_env()) as status:
        while status.exit_code is None:  # pragma: no branch
            status.wait()

    master_fds = [result[0] for result in pty_spy.spy_return_list]
    assert len(master_fds) == 2  # tty path taken for stdout and stderr
    for fd in master_fds:
        with pytest.raises(OSError, match="Bad file descriptor"):
            os.fstat(fd)


@pytest.mark.skipif(sys.platform == "win32", reason="pty is Unix-only")
def test_get_stream_file_no_closes_each_pty_fd_once(mocker: MockerFixture) -> None:
    """Each pty fd must be closed exactly once.

    The child fd is closed once the child has inherited it; closing it a second time on generator teardown can race a
    parallel run that has reused the freed fd number, corrupting the sibling's fd (see #3975).

    """
    main_fd, child_fd = 11, 22
    mocker.patch.object(local_sub_process, "_pty", return_value=(main_fd, child_fd))
    close_spy = mocker.patch.object(os, "close")

    gen = LocalSubProcessExecuteInstance.get_stream_file_no("stdout")
    assert next(gen) == child_fd
    assert gen.send(MagicMock()) == main_fd
    gen.close()

    closed = [call.args[0] for call in close_spy.call_args_list]
    assert closed.count(child_fd) == 1
    assert closed.count(main_fd) == 1


@pytest.mark.skipif(sys.platform != "win32", reason="overlapped I/O reader is Windows-only")
def test_read_via_thread_windows_stops_while_read_pending(mocker: MockerFixture) -> None:
    """A never-completing overlapped read must not keep the reader thread alive after stop is set."""
    pending = OSError()
    pending.winerror = read_via_thread_windows.ERROR_IO_INCOMPLETE
    overlapped = mocker.MagicMock()
    overlapped.getresult.side_effect = pending  # the read never completes
    mocker.patch.object(
        read_via_thread_windows, "_overlapped", mocker.MagicMock(Overlapped=mocker.MagicMock(return_value=overlapped))
    )

    reader = read_via_thread_windows.ReadViaThreadWindows(
        file_no=0, handler=mocker.MagicMock(return_value=0), name="pending", drain=False
    )
    reader.thread.start()
    deadline = time.monotonic() + 5
    while not overlapped.getresult.called and time.monotonic() < deadline:
        time.sleep(0.01)
    reader.stop.set()
    reader.thread.join(timeout=5)

    assert not reader.thread.is_alive()


@pytest.mark.parametrize("tty_mode", ["on", "off"])
def test_local_subprocess_tty(monkeypatch: MonkeyPatch, mocker: MockerFixture, tty_mode: str) -> None:
    monkeypatch.setenv("COLUMNS", "100")
    monkeypatch.setenv("LINES", "100")
    tty = tty_mode == "on"
    mocker.patch("sys.stdout.isatty", return_value=tty)
    mocker.patch("sys.stderr.isatty", return_value=tty)
    try:
        import termios  # ruff:ignore[unused-import, import-outside-top-level]
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
    with executor.call(request, show=False, out_err=out_err.out_err, env=_create_mock_env()) as status:
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
    exe = shutil.which("python3") or shutil.which("python")
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
    with executor.call(request, show=False, out_err=out_err.out_err, env=_create_mock_env()) as status:
        while status.exit_code is None:  # pragma: no branch
            status.wait()
    outcome = status.outcome

    assert outcome is not None
    assert outcome.out == key


@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific tests")
def test_read_via_thread_eintr_during_select(mocker: MockerFixture) -> None:
    """Test that EINTR during selector.select() is handled correctly."""
    # Create a pipe
    data_received: list[bytes] = []
    eintr_raised = [False]

    def handler(data: bytes) -> int:
        data_received.append(data)
        return len(data)

    original_select = selectors.DefaultSelector.select

    def mock_select(self: Any, timeout: float | None = None) -> list[tuple[selectors.SelectorKey, int]]:
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
    """Test that EINTR during os.read() is handled correctly."""
    data_received: list[bytes] = []
    original_read = os.read
    call_count = [0]

    def handler(data: bytes) -> int:
        data_received.append(data)
        return len(data)

    def mock_read(fd: int, n: int) -> bytes:
        call_count[0] += 1
        if call_count[0] == 1:
            err = OSError("Interrupted")
            err.errno = errno.EINTR
            raise err
        return original_read(fd, n)

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
    """Test that EBADF during os.read() is handled correctly."""
    data_received: list[bytes] = []

    def handler(data: bytes) -> int:
        data_received.append(data)
        return len(data)

    def mock_read(fd: int, n: int) -> NoReturn:  # ruff:ignore[unused-function-argument]
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
    """Test drain_stream when there's no data ready."""
    data_received: list[bytes] = []

    def handler(data: bytes) -> int:
        data_received.append(data)
        return len(data)

    read_fd, write_fd = os.pipe()
    try:
        os.close(write_fd)
        reader = ReadViaThreadUnix(read_fd, handler, "test", drain=True)
        reader._drain_stream()  # ruff:ignore[private-member-access]
    finally:
        with contextlib.suppress(OSError):
            os.close(read_fd)
    assert len(data_received) == 0
