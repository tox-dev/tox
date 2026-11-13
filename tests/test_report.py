from __future__ import annotations

import logging
import os
import sys
from io import TextIOWrapper
from typing import TYPE_CHECKING

import pytest
from colorama import Style, deinit

from tox.report import NamedBytesIO, setup_report

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from tox.pytest import CaptureFixture


@pytest.mark.parametrize("color", [pytest.param(True, id="on"), pytest.param(False, id="off")])
@pytest.mark.parametrize("verbosity", range(7))
def test_setup_report(mocker: MockerFixture, capsys: CaptureFixture, verbosity: int, color: bool) -> None:
    color_init = mocker.patch("tox.report.init", autospec=True)

    _emit_report(verbosity, color)

    assert color_init.call_count == int(color)
    out, err = capsys.readouterr()
    assert not err
    assert out
    assert "filelock" not in out
    assert "distlib.util" not in out
    msg_count = min(verbosity + 1, 5) + (verbosity >= 4)  # debug level also logs the logger setup
    assert len(out.splitlines()) == msg_count, out
    assert (Style.RESET_ALL in out) is color


def _emit_report(verbosity: int, color: bool) -> None:
    setup_report(verbosity=verbosity, is_colored=color)
    try:
        _emit_test_log_messages()
    finally:
        deinit()


def _emit_test_log_messages() -> None:
    logging.critical("critical")
    logging.error("error")
    logging.warning("%s%s> %s", "warning", "foo", "bar")  # special warning: auto-colored
    logging.info("info")
    logging.debug("debug")
    logging.log(logging.NOTSET, "not-set")  # this should not be logged
    for name in ("distlib.util", "filelock"):
        logger = logging.getLogger(name)
        logger.warning("%s-warn", name)
        logger.info("%s-info", name)
        logger.debug("%s-debug", name)
        logger.log(logging.NOTSET, "%s-notset", name)


@pytest.mark.parametrize("verbosity", [4, 5, 6])
def test_setup_report_debug_location(capsys: CaptureFixture, verbosity: int) -> None:
    _emit_report(verbosity, color=False)

    first_line = capsys.readouterr().out.splitlines()[0]
    int(first_line.split(" ")[1])  # first element is an int number
    assert f"[tox{os.sep}report.py" in first_line  # relative file location


@pytest.mark.parametrize("verbosity", [4, 5, 6])
@pytest.mark.parametrize(
    ("color", "expected_warning_text"),
    [
        pytest.param(True, "W\x1b[0m\x1b[36m warning\x1b[22mfoo\x1b[2m>\x1b[0m bar\x1b[0m\x1b[2m", id="on"),
        pytest.param(False, "warningfoo> bar", id="off"),
    ],
)
def test_setup_report_warning_text(
    mocker: MockerFixture, capsys: CaptureFixture, verbosity: int, color: bool, expected_warning_text: str
) -> None:
    mocker.patch("tox.report.init", autospec=True)

    _emit_report(verbosity, color)

    lines = capsys.readouterr().out.splitlines()
    assert expected_warning_text in lines[3]


def test_setup_report_degrades_logged_output(
    redirected_cp1252_output: TextIOWrapper, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "stdout", redirected_cp1252_output)
    monkeypatch.setattr(sys, "stderr", redirected_cp1252_output)

    setup_report(verbosity=3, is_colored=False)
    logging.critical("box %s and path %s", "\u2500", "\u80e1")
    redirected_cp1252_output.flush()
    redirected_cp1252_output.seek(0)

    assert "box \\u2500 and path \\u80e1" in redirected_cp1252_output.read()


@pytest.fixture
def redirected_cp1252_output() -> TextIOWrapper:
    return TextIOWrapper(NamedBytesIO("out"), encoding="cp1252", errors="strict")


def test_setup_report_degrades_direct_output(
    redirected_cp1252_output: TextIOWrapper, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "stdout", redirected_cp1252_output)
    monkeypatch.setattr(sys, "stderr", redirected_cp1252_output)

    setup_report(verbosity=3, is_colored=False)
    sys.stdout.write("box \u2500 and path \u80e1")
    redirected_cp1252_output.flush()
    redirected_cp1252_output.seek(0)

    assert redirected_cp1252_output.read() == "box \\u2500 and path \\u80e1"


def test_suspended_output_degrades_unencodable_text(
    redirected_cp1252_output: TextIOWrapper, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
) -> None:
    monkeypatch.setattr(sys, "stdout", redirected_cp1252_output)
    monkeypatch.setattr(sys, "stderr", redirected_cp1252_output)
    mocker.patch("tox.report.locale.getpreferredencoding", autospec=True, return_value="cp1252")
    with setup_report(verbosity=3, is_colored=False).suspend_out_err(True) as (stdout, _):
        stdout.write("box \u2500")
        stdout.flush()
        stdout.seek(0)
        assert stdout.read() == "box \\u2500"
