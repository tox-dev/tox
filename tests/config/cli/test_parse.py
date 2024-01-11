from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

from tox.config.cli.parse import get_options

if TYPE_CHECKING:
    from tox.pytest import CaptureFixture


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
        assert logger.disabled
    logging.error("E")
    logging.warning("W")
    logging.info("I")
    logging.debug("D")

    out, _err = capsys.readouterr()
    assert out == "ROOT: E\nROOT: W\nROOT: I\n"


@pytest.mark.parametrize("arg", ["-av", "-va"])
def test_verbosity(arg: str) -> None:
    result = get_options(arg)
    assert result.parsed.verbosity == 3
