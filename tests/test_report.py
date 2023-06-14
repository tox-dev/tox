from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

import pytest
from colorama import Style, deinit

from tox.report import setup_report

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from tox.pytest import CaptureFixture


@pytest.mark.parametrize("color", [True, False], ids=["on", "off"])
@pytest.mark.parametrize("verbosity", range(7))
def test_setup_report(mocker: MockerFixture, capsys: CaptureFixture, verbosity: int, color: bool) -> None:
    color_init = mocker.patch("tox.report.init")

    setup_report(verbosity=verbosity, is_colored=color)
    try:
        logging.critical("critical")
        logging.error("error")
        # special warning line that should be auto-colored
        logging.warning("%s%s> %s", "warning", "foo", "bar")
        logging.info("info")
        logging.debug("debug")
        logging.log(logging.NOTSET, "not-set")  # this should not be logged
        disabled = "distlib.util", "filelock"
        for name in disabled:
            logger = logging.getLogger(name)
            logger.warning("%s-warn", name)
            logger.info("%s-info", name)
            logger.debug("%s-debug", name)
            logger.log(logging.NOTSET, "%s-notset", name)
    finally:
        deinit()

    assert color_init.call_count == (1 if color else 0)

    msg_count = min(verbosity + 1, 5)
    is_debug_or_more = verbosity >= 4
    if is_debug_or_more:
        msg_count += 1  # we log at debug level setting up the logger

    out, err = capsys.readouterr()
    assert not err
    assert out
    assert "filelock" not in out
    assert "distlib.util" not in out
    lines = out.splitlines()
    assert len(lines) == msg_count, out

    if is_debug_or_more and lines:  # assert we start with relative created, contain path
        line = lines[0]
        int(line.split(" ")[1])  # first element is an int number
        assert f"[tox{os.sep}report.py" in line  # relative file location

    if color:
        assert f"{Style.RESET_ALL}" in out
        # check that our Warning line using special format was colored
        expected_warning_text = "W\x1b[0m\x1b[36m warning\x1b[22mfoo\x1b[2m>\x1b[0m bar\x1b[0m\x1b[2m"
    else:
        assert f"{Style.RESET_ALL}" not in out
        expected_warning_text = "warningfoo> bar"
    if verbosity >= 4:  # where warnings are logged
        assert expected_warning_text in lines[3]
