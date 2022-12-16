from __future__ import annotations

import sys
from argparse import Action

import pytest
from pytest_mock import MockerFixture

from tox.config.cli.parser import Parsed, ToxParser
from tox.pytest import CaptureFixture, MonkeyPatch


def test_parser_const_with_default_none(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("TOX_ALPHA", "2")
    parser = ToxParser.base()
    parser.add_argument(
        "-a",
        dest="alpha",
        action="store_const",
        const=1,
        default=None,
        help="sum the integers (default: find the max)",
    )
    parser.fix_defaults()

    result = parser.parse_args([])
    assert result.alpha == 2


@pytest.mark.parametrize("is_atty", [True, False])
@pytest.mark.parametrize("no_color", [None, "0", "1", "", "\t", " ", "false", "true"])
@pytest.mark.parametrize("force_color", [None, "0", "1"])
@pytest.mark.parametrize("tox_color", [None, "bad", "no", "yes"])
@pytest.mark.parametrize("term", [None, "xterm", "dumb"])
def test_parser_color(
    monkeypatch: MonkeyPatch,
    mocker: MockerFixture,
    no_color: str | None,
    force_color: str | None,
    tox_color: str | None,
    is_atty: bool,
    term: str | None,
) -> None:
    for key, value in {
        "NO_COLOR": no_color,
        "TOX_COLORED": tox_color,
        "FORCE_COLOR": force_color,
        "TERM": term,
    }.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    stdout_mock = mocker.patch("tox.config.cli.parser.sys.stdout")
    stdout_mock.isatty.return_value = is_atty

    if tox_color in ("yes", "no"):
        expected = tox_color == "yes"
    elif bool(no_color):
        expected = False
    elif force_color == "1":
        expected = True
    elif term == "dumb":
        expected = False
    else:
        expected = is_atty

    is_colored = ToxParser.base().parse_args([], Parsed()).is_colored
    assert is_colored is expected


def test_parser_unsupported_type() -> None:
    parser = ToxParser.base()
    parser.add_argument("--magic", action="store", default=None)
    with pytest.raises(TypeError) as context:
        parser.fix_defaults()
    action = context.value.args[0]
    assert isinstance(action, Action)
    assert action.dest == "magic"


def test_sub_sub_command() -> None:
    parser = ToxParser.base()
    with pytest.raises(RuntimeError, match="no sub-command group allowed"):
        parser.add_command("c", [], "help", lambda s: 0)  # pragma: no cover - the lambda will never be run # noqa: U100


def test_parse_known_args_not_set(mocker: MockerFixture) -> None:
    mocker.patch.object(sys, "argv", ["a", "--help"])
    parser = ToxParser.base()
    _, unknown = parser.parse_known_args(None)
    assert unknown == ["--help"]


def test_parser_hint(capsys: CaptureFixture) -> None:
    parser = ToxParser.base()
    with pytest.raises(SystemExit):
        parser.parse_args("foo")
    out, err = capsys.readouterr()
    assert err.endswith("hint: if you tried to pass arguments to a command use -- to separate them from tox ones\n")
