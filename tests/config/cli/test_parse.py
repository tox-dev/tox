from __future__ import annotations

import logging

import pytest

from tox.config.cli.parse import get_options
from tox.pytest import CaptureFixture
from tox.report import LowerInfoLevel


def test_help_does_not_default_cmd(capsys: CaptureFixture) -> None:
    with pytest.raises(SystemExit):
        get_options("-h")
    out, err = capsys.readouterr()
    assert not err
    assert "--verbose" in out
    assert "subcommands:" in out


def test_verbosity_guess_miss_match(capsys: CaptureFixture) -> None:
    result = get_options("-rv")
    assert result.parsed.verbosity == 3

    assert logging.getLogger().level == logging.INFO

    for name in ("distlib.util", "filelock"):
        logger = logging.getLogger(name)
        for logging_filter in logger.filters:  # pragma: no branch # never empty
            if isinstance(logging_filter, LowerInfoLevel):  # pragma: no branch # we always find it
                assert logging_filter.level == logging.INFO
                break

    logging.error("E")
    logging.warning("W")
    logging.info("I")
    logging.debug("D")

    out, err = capsys.readouterr()
    assert out == "ROOT: E\nROOT: W\nROOT: I\n"


@pytest.mark.parametrize("arg", ["-av", "-va"])
def test_verbosity(arg: str) -> None:
    result = get_options(arg)
    assert result.parsed.verbosity == 3
