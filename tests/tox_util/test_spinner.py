from __future__ import annotations

import os
import sys
import time
from typing import TYPE_CHECKING

import pytest
import time_machine
from colorama import Fore

from tox.util.spinner import Spinner, td_human_readable

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from tox.pytest import CaptureFixture, MonkeyPatch


@time_machine.travel("2012-01-14", tick=False)
def test_spinner(capfd: CaptureFixture, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    with Spinner(refresh_rate=100) as spin:
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
    with Spinner(refresh_rate=100, enabled=False) as spin:
        spin.add("x")
        for _ in range(len(spin.frames)):
            spin.render_frame()
        spin.finalize("x", "done", str(Fore.GREEN))
        spin.clear()
    out, err = capfd.readouterr()
    assert out.startswith(f"{Fore.GREEN}x: done in 0"), out
    assert out.endswith(f" seconds{Fore.RESET}{os.linesep}"), out
    assert not err


@time_machine.travel("2012-01-14", tick=False)
def test_spinner_progress(capfd: CaptureFixture, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    with Spinner() as spin:
        for _ in range(len(spin.frames)):  # pragma: no branch  # other outcome untested
            spin.stream.write("\n")
            time.sleep(spin.refresh_rate)  # simplint: ignore[sleep-in-test]  # waits for a real frame change

    out, err = capfd.readouterr()
    assert not err
    assert len({i.strip() for i in out.split("[0]")}) > len(spin.frames) / 2


@pytest.mark.parametrize(
    ("hide_cursor", "show_cursor"),
    [
        pytest.param(
            "\x1b[?25l",
            "\x1b[?25h",
            id="posix",
            marks=pytest.mark.skipif(os.name != "posix", reason="posix cursor escape codes"),
        ),
        pytest.param("", "", id="windows", marks=pytest.mark.skipif(os.name == "posix", reason="no cursor escapes")),
    ],
)
@time_machine.travel("2012-01-14", tick=False)
def test_spinner_atty(capfd: CaptureFixture, monkeypatch: MonkeyPatch, hide_cursor: str, show_cursor: str) -> None:
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    with Spinner(refresh_rate=100) as spin:
        spin.stream.write("\n")
    out, _err = capfd.readouterr()
    lines = out.split("\n")
    expected = [
        f"{hide_cursor}\r{spin.CLEAR_LINE}\r{spin.frames[0]} [0]",
        f"\r\x1b[K{show_cursor}",
    ]
    assert lines == expected


@time_machine.travel("2012-01-14", tick=False)
@pytest.mark.flaky(max_runs=3, min_passes=1)
def test_spinner_report(capfd: CaptureFixture, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    with Spinner(refresh_rate=100) as spin:
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
    with Spinner(refresh_rate=100) as spin:
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
    stdout = mocker.patch("tox.util.spinner.sys.stdout", autospec=True)
    stdout.encoding = "ascii"
    with Spinner(refresh_rate=100) as spin:
        for _ in range(len(spin.frames)):  # pragma: no branch  # other outcome untested
            spin.render_frame()
    out, err = capfd.readouterr()
    assert not err
    assert not out
    written = "".join({i[0][0] for i in stdout.write.call_args_list})
    assert all(f in written for f in spin.frames)


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        pytest.param(0, "0 seconds", id="0-0-space-seconds"),
        pytest.param(1.0, "1 second", id="1-dot-0-1-space-second"),
        pytest.param(4.0, "4 seconds", id="4-dot-0-4-space-seconds"),
        pytest.param(4.13, "4.13 seconds", id="4-dot-13-4-dot-13-space-seconds"),
        pytest.param(4.137, "4.14 seconds", id="4-dot-137-4-dot-14-space-seconds"),
        pytest.param(42.12345, "42.12 seconds", id="42-dot-12345-42-dot-12-space-seconds"),
        pytest.param(60, "1 minute", id="60-1-space-minute"),
        pytest.param(61, "1 minute 1 second", id="61-1-space-minute-space-1-space-second"),
        pytest.param(120, "2 minutes", id="120-2-space-minutes"),
        pytest.param(
            40 * 24 * 60 * 60 + 5 * 60,
            "40 days 5 minutes",
            id="40-space-star-space-24-space-star-space-60-space-star-space-60-space-plus-space-5-space-star-space-60-40-space-days-space-5-space-minutes",
        ),
        pytest.param(
            40 * 24 * 60 * 60 + 4 * 60 * 60 + 5 * 60 + 1.5,
            "40 days 4 hours 5 minutes 1.5 seconds",
            id="40-space-star-space-24-space-star-space-60-space-star-space-60-space-plus-space-4-space-star-space-60-space-star-space-60-space-plus-space-5-space-star-space-60-space-plus-space-1-dot-5-40-space-days-space-4-space-hours-space-5-space-minutes-space-1-dot-5-space-seconds",
        ),
    ],
)
def test_td_human_readable(seconds: float, expected: str) -> None:
    assert td_human_readable(seconds) == expected
