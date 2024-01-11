from __future__ import annotations

import os
import sys
import time
from typing import TYPE_CHECKING

import pytest
import time_machine
from colorama import Fore

from tox.util import spinner

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from tox.pytest import CaptureFixture, MonkeyPatch


@time_machine.travel("2012-01-14", tick=False)
def test_spinner(capfd: CaptureFixture, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    with spinner.Spinner(refresh_rate=100) as spin:
        for _ in range(len(spin.frames)):
            spin.stream.write("\n")
            spin.render_frame()
        spin.stream.write("\n")
    out, _err = capfd.readouterr()
    lines = out.split("\n")
    expected = [f"\r{spin.CLEAR_LINE}\r{i} [0]" for i in spin.frames] + [
        f"\r{spin.CLEAR_LINE}\r{spin.frames[0]} [0]",
        f"\r{spin.CLEAR_LINE}",
    ]
    assert lines == expected


@time_machine.travel("2012-01-14", tick=False)
def test_spinner_disabled(capfd: CaptureFixture) -> None:
    with spinner.Spinner(refresh_rate=100, enabled=False) as spin:
        spin.add("x")
        for _ in range(len(spin.frames)):
            spin.render_frame()
        spin.finalize("x", "done", Fore.GREEN)
        spin.clear()
    out, err = capfd.readouterr()
    assert out == f"{Fore.GREEN}x: done in 0 seconds{Fore.RESET}{os.linesep}", out
    assert not err


@time_machine.travel("2012-01-14", tick=False)
def test_spinner_progress(capfd: CaptureFixture, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    with spinner.Spinner() as spin:
        for _ in range(len(spin.frames)):  # pragma: no branch
            spin.stream.write("\n")
            time.sleep(spin.refresh_rate)

    out, err = capfd.readouterr()
    assert not err
    assert len({i.strip() for i in out.split("[0]")}) > len(spin.frames) / 2


@time_machine.travel("2012-01-14", tick=False)
def test_spinner_atty(capfd: CaptureFixture, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    with spinner.Spinner(refresh_rate=100) as spin:
        spin.stream.write("\n")
    out, _err = capfd.readouterr()
    lines = out.split("\n")
    posix = os.name == "posix"
    expected = [
        "{}\r{}\r{} [0]".format("\x1b[?25l" if posix else "", spin.CLEAR_LINE, spin.frames[0]),
        "\r\x1b[K{}".format("\x1b[?25h" if posix else ""),
    ]
    assert lines == expected


@time_machine.travel("2012-01-14", tick=False)
@pytest.mark.flaky(max_runs=3, min_passes=1)
def test_spinner_report(capfd: CaptureFixture, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    with spinner.Spinner(refresh_rate=100) as spin:
        spin.stream.write(os.linesep)
        spin.add("ok")
        spin.add("fail")
        spin.add("skip")
        spin.succeed("ok")
        spin.fail("fail")
        spin.skip("skip")
    out, err = capfd.readouterr()
    lines = out.split(os.linesep)
    del lines[0]
    expected = [
        f"\r{spin.CLEAR_LINE}{Fore.GREEN}ok: OK ✔ in 0 seconds{Fore.RESET}",
        f"\r{spin.CLEAR_LINE}{Fore.RED}fail: FAIL ✖ in 0 seconds{Fore.RESET}",
        f"\r{spin.CLEAR_LINE}{Fore.YELLOW}skip: SKIP ⚠ in 0 seconds{Fore.RESET}",
        f"\r{spin.CLEAR_LINE}",
    ]
    assert lines == expected
    assert not err


def test_spinner_long_text(capfd: CaptureFixture, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    with spinner.Spinner(refresh_rate=100) as spin:
        spin.stream.write("\n")
        spin.add("a" * 60)
        spin.add("b" * 60)
        spin.render_frame()
        spin.stream.write("\n")
    out, err = capfd.readouterr()
    assert not err
    expected = [
        f"\r{spin.CLEAR_LINE}\r{spin.frames[1]} [2] {'a' * 60} |...",
        f"\r{spin.CLEAR_LINE}",
    ]
    lines = out.split("\n")
    del lines[0]
    assert lines == expected


def test_spinner_stdout_not_unicode(capfd: CaptureFixture, mocker: MockerFixture) -> None:
    stdout = mocker.patch("tox.util.spinner.sys.stdout")
    stdout.encoding = "ascii"
    with spinner.Spinner(refresh_rate=100) as spin:
        for _ in range(len(spin.frames)):  # pragma: no branch
            spin.render_frame()
    out, err = capfd.readouterr()
    assert not err
    assert not out
    written = "".join({i[0][0] for i in stdout.write.call_args_list})
    assert all(f in written for f in spin.frames)


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0, "0 seconds"),
        (1.0, "1 second"),
        (4.0, "4 seconds"),
        (4.13, "4.13 seconds"),
        (4.137, "4.14 seconds"),
        (42.12345, "42.12 seconds"),
        (60, "1 minute"),
        (61, "1 minute 1 second"),
        (120, "2 minutes"),
        (40 * 24 * 60 * 60 + 5 * 60, "40 days 5 minutes"),
        (40 * 24 * 60 * 60 + 4 * 60 * 60 + 5 * 60 + 1.5, "40 days 4 hours 5 minutes 1.5 seconds"),
    ],
)
def test_td_human_readable(seconds: float, expected: str) -> None:
    assert spinner.td_human_readable(seconds) == expected
