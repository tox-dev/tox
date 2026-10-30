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


@pytest.mark.parametrize(
    ("argv", "factors"),
    [
        pytest.param(("-f", "py", "legacy"), [["py", "legacy"]], id="command-name"),
        pytest.param(("-f", "-1", "list"), [["-1", "list"]], id="negative-number"),
        pytest.param(("-f", "-.5", "list"), [["-.5", "list"]], id="negative-fraction"),
    ],
)
def test_multi_value_option_keeps_its_values(argv: tuple[str, ...], factors: list[list[str]]) -> None:
    result = get_options(*argv)
    assert result.parsed.factors == factors


def test_multi_value_option_stops_at_the_next_option() -> None:
    result = get_options("-f", "py", "-v", "list")
    assert result.parsed.command == "list"
    assert result.parsed.factors == [["py"]]
