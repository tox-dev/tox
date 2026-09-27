from __future__ import annotations

import sys
from argparse import Action
from typing import TYPE_CHECKING, Literal, get_args

import pytest

from tox.config.cli.parser import Parsed, ToxParser

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Final

    from pytest_mock import MockerFixture

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


def test_parser_command_without_core_inherit() -> None:
    parser = ToxParser.core()
    parser.add_command("noop", [], "a command without inherited core flags", lambda _: 0, inherit=frozenset())

    result = parser.parse_args(["noop"])
    assert result.command == "noop"
    assert result.work_dir is None


def test_parser_help_shows_default_source(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("TOX_VERBOSE", "5")
    parser = ToxParser.core()

    assert "-> from env var TOX_VERBOSE" in parser.format_help()


@pytest.mark.parametrize("is_atty", [True, False])
@pytest.mark.parametrize("no_color", [None, "0", "1", "", "\t", " ", "false", "true"])
@pytest.mark.parametrize("force_color", [None, "", "0", "1", "always", "not an empty string"])
@pytest.mark.parametrize("tox_color", [None, "bad", "no", "yes"])
@pytest.mark.parametrize("tty_compatible", [None, "", "0", "1", "other"])
@pytest.mark.parametrize("term", [None, "xterm", "dumb"])
def test_parser_color(
    monkeypatch: MonkeyPatch,
    mocker: MockerFixture,
    no_color: str | None,
    force_color: str | None,
    tox_color: str | None,
    tty_compatible: str | None,
    is_atty: bool,
    term: str | None,
) -> None:
    for key, value in {
        "NO_COLOR": no_color,
        "TOX_COLORED": tox_color,
        "FORCE_COLOR": force_color,
        "TTY_COMPATIBLE": tty_compatible,
        "TERM": term,
    }.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    stdout_mock = mocker.patch("tox.config.cli.parser.sys.stdout")
    stdout_mock.isatty.return_value = is_atty

    if tox_color in {"yes", "no"}:
        expected = tox_color == "yes"
    elif bool(no_color):
        expected = False
    elif bool(force_color):
        expected = True
    elif tty_compatible in {"0", "1"}:
        expected = tty_compatible == "1"
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


def test_parser_choices_become_literal_type(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("TOX_MODE", "fast")
    parser = ToxParser.base()
    action = parser.add_argument("--mode", choices=["fast", "slow", "medium"], default="fast")
    of_type = parser.get_type(action)
    assert of_type == Literal["fast", "slow", "medium"]
    assert set(get_args(of_type)) == {"fast", "slow", "medium"}


@pytest.mark.parametrize("value_type", [pytest.param(str, id="str"), pytest.param(None, id="implicit-str")])
@pytest.mark.parametrize("default", [pytest.param([], id="empty-default"), pytest.param(None, id="no-default")])
@pytest.mark.parametrize("source", [pytest.param("env", id="env"), pytest.param("file", id="file")])
@pytest.mark.parametrize(
    ("action", "nargs", "expected"),
    [
        pytest.param("store", "+", ["old", "new"], id="store-one-or-more"),
        pytest.param("store", "*", ["old", "new"], id="store-zero-or-more"),
        pytest.param("store", 1, ["old", "new"], id="store-one"),
        pytest.param("store", 2, ["old", "new"], id="store-two"),
        pytest.param("append", "+", [["old"], ["new"]], id="append-one-or-more"),
        pytest.param("append", "*", [["old"], ["new"]], id="append-zero-or-more"),
        pytest.param("append", 1, [["old"], ["new"]], id="append-one"),
        pytest.param("append", 2, [["old"], ["new"]], id="append-two"),
        pytest.param("append", None, ["old", "new"], id="append-scalar"),
    ],
)
def test_parser_list_defaults(
    monkeypatch: MonkeyPatch,
    value_type: type[str] | None,
    default: list[str] | None,
    nargs: str | int | None,
    action: str,
    expected: list[str] | list[list[str]],
    source: str,
    tmp_path: Path,
) -> None:
    if source == "env":
        monkeypatch.setenv("TOX_LABELS", "old;new")
    else:
        config_file: Final[Path] = tmp_path / "user.ini"
        config_file.write_text("[tox]\nlabels =\n  old\n  new\n", encoding="utf-8")
        monkeypatch.setenv("TOX_USER_CONFIG_FILE", str(config_file))
    parser: Final[ToxParser] = ToxParser.base()
    parser.add_argument("-m", dest="labels", action=action, nargs=nargs, default=default, type=value_type)
    parser.fix_defaults()
    assert parser.parse_args([]).labels == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [pytest.param("old;new", ["old", "new"], id="valid"), pytest.param("old;bad", [], id="invalid")],
)
def test_parser_multi_value_choices(monkeypatch: MonkeyPatch, value: str, expected: list[str]) -> None:
    monkeypatch.setenv("TOX_LABELS", value)
    parser: Final[ToxParser] = ToxParser.base()
    parser.add_argument("-m", dest="labels", nargs="+", default=[], choices=["old", "new"])
    parser.fix_defaults()
    assert parser.parse_args([]).labels == expected


@pytest.mark.parametrize(
    ("action", "nargs", "expected"),
    [
        pytest.param("store", "+", [12, 34], id="store"),
        pytest.param("append", 1, [[12], [34]], id="append-one"),
        pytest.param("append", "+", [[12], [34]], id="append-many"),
    ],
)
def test_parser_multi_value_integers(
    monkeypatch: MonkeyPatch,
    action: str,
    nargs: str | int,
    expected: list[int] | list[list[int]],
) -> None:
    monkeypatch.setenv("TOX_VALUES", "12;34")
    parser: Final[ToxParser] = ToxParser.base()
    parser.add_argument("--values", action=action, nargs=nargs, type=int)
    parser.fix_defaults()
    assert parser.parse_args([]).values == expected


def test_sub_sub_command() -> None:
    parser = ToxParser.base()
    with pytest.raises(RuntimeError, match="no sub-command group allowed"):
        parser.add_command(
            "c",
            [],
            "help",
            lambda s: 0,  # ruff:ignore[unused-lambda-argument]
        )  # pragma: no cover - the lambda will never be run


def test_parse_known_args_not_set(mocker: MockerFixture) -> None:
    mocker.patch.object(sys, "argv", ["a", "--help"])
    parser = ToxParser.base()
    _, unknown = parser.parse_known_args(None)
    assert unknown == ["--help"]


def test_parser_hint(capsys: CaptureFixture) -> None:
    parser = ToxParser.base()
    with pytest.raises(SystemExit):
        parser.parse_args("foo")
    _out, err = capsys.readouterr()
    assert err.endswith("hint: if you tried to pass arguments to a command use -- to separate them from tox ones\n")
