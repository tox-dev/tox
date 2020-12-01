import logging
import os

import pytest
from colorama import Style, deinit
from pytest_mock import MockerFixture

from tox.pytest import CaptureFixture
from tox.report import setup_report


@pytest.mark.parametrize("color", [True, False], ids=["on", "off"])
@pytest.mark.parametrize("verbosity", range(7))
def test_setup_report(mocker: MockerFixture, capsys: CaptureFixture, verbosity: int, color: bool) -> None:
    color_init = mocker.patch("tox.report.init")

    setup_report(verbosity=verbosity, is_colored=color)
    try:
        logging.critical("critical")
        logging.error("error")
        logging.warning("warning")
        logging.info("info")
        logging.debug("debug")
        logging.log(logging.NOTSET, "not-set")  # this should not be logged
        lowered = "distlib.util", "filelock"
        for name in lowered:
            logger = logging.getLogger(name)
            logger.warning(f"{name}-warn")
            logger.info(f"{name}-info")
            logger.debug(f"{name}-debug")
            logger.log(logging.NOTSET, f"{name}-notset")
    finally:
        deinit()

    assert color_init.call_count == (1 if color else 0)

    msg_count = min(verbosity + 1, 5)
    msg_count += (1 if verbosity >= 2 else 0) * len(lowered)  # warning lowered
    is_debug_or_more = verbosity >= 4
    if is_debug_or_more:
        msg_count += 1  # we log at debug level setting up the logger
        msg_count += (2 if verbosity >= 4 else 1) * len(lowered)

    out, err = capsys.readouterr()
    assert not err
    assert out
    lines = out.splitlines()
    assert len(lines) == msg_count, out

    if is_debug_or_more and lines:  # assert we start with relative created, contain path
        line = lines[0]
        int(line.split(" ")[1])  # first element is an int number
        assert f"[tox{os.sep}report.py" in line  # relative file location

    if color:
        assert f"{Style.RESET_ALL}" in out
    else:
        assert f"{Style.RESET_ALL}" not in out
