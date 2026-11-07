from __future__ import annotations

import os
import sys
from argparse import Action, Namespace
from typing import TYPE_CHECKING, Final, Literal, get_args

import pytest

from tox.config.cli.parser import Parsed, ToxParser

if TYPE_CHECKING:
    from pathlib import Path

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


@pytest.mark.parametrize(
    ("nargs", "args", "command", "values"),
    [
        pytest.param("+", ("--values", "one", "list"), "legacy", ["one", "list"], id="one-or-more"),
        pytest.param("*", ("--values", "one", "list"), "legacy", ["one", "list"], id="zero-or-more-values"),
        pytest.param("*", ("--values", "list"), "list", [], id="zero-or-more-before-command"),
        pytest.param("?", ("--values", "list"), "list", None, id="optional-before-command"),
        pytest.param("?", ("--values", "one", "list"), "list", "one", id="optional-value"),
        pytest.param(2, ("--values", "one", "list", "legacy"), "legacy", ["one", "list"], id="exact-count"),
        pytest.param(
            "+", ("--values", "one", "-2", "list"), "legacy", ["one", "-2", "list"], id="negative-number-value"
        ),
        pytest.param(2, ("--values", "one", "-2", "list"), "list", ["one", "-2"], id="negative-number-exact-count"),
    ],
)
def test_parser_command_scan_respects_option_values(
    nargs: str | int, args: tuple[str, ...], command: str, values: str | list[str] | None
) -> None:
    parser: Final[ToxParser] = ToxParser.core()
    parser.add_argument("--values", nargs=nargs)
    parser.add_command("legacy", [], "run", lambda _state: 0)
    parser.add_command("list", [], "list", lambda _state: 0)

    result: Final[Namespace] = parser.parse_args(args)
    assert (result.command, result.values) == (command, values)


def test_parser_help_shows_default_source(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("TOX_VERBOSE", "5")
    parser = ToxParser.core()

    assert "-> from env var TOX_VERBOSE" in parser.format_help()


@pytest.mark.parametrize(
    ("env", "is_atty", "expected"),
    [
        pytest.param({"TOX_COLORED": "yes"}, False, True, id="tox-yes-over-tty"),
        pytest.param({"TOX_COLORED": "no", "FORCE_COLOR": "1"}, True, False, id="tox-no-over-force"),
        pytest.param({"NO_COLOR": "1", "FORCE_COLOR": "1"}, True, False, id="no-color-over-force"),
        pytest.param({"FORCE_COLOR": "1"}, False, True, id="force-color"),
        pytest.param({"FORCE_COLOR": "always"}, False, True, id="force-color-always"),
        pytest.param({"FORCE_COLOR": ""}, True, True, id="empty-force-color-uses-tty"),
        pytest.param({"TTY_COMPATIBLE": "1"}, False, True, id="tty-compatible-1"),
        pytest.param({"TTY_COMPATIBLE": "0"}, True, False, id="tty-compatible-0"),
        pytest.param({"TERM": "dumb"}, True, False, id="term-dumb"),
        pytest.param({}, True, True, id="tty"),
        pytest.param({}, False, False, id="no-tty"),
    ],
)
def test_parser_color(
    monkeypatch: MonkeyPatch,
    mocker: MockerFixture,
    env: dict[str, str],
    is_atty: bool,
    expected: bool,
) -> None:
    color_vars = {"NO_COLOR", "TOX_COLORED", "FORCE_COLOR", "TTY_COMPATIBLE", "TERM"}
    monkeypatch.setattr(os, "environ", {k: v for k, v in os.environ.items() if k not in color_vars} | env)
    mocker.patch("tox.config.cli.parser.sys.stdout").isatty.return_value = is_atty

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
    of_type = parser.get_type(parser.add_argument("--mode", choices=["fast", "slow", "medium"], default="fast"))
    assert of_type == Literal["fast", "slow", "medium"]
    assert set(get_args(of_type)) == {"fast", "slow", "medium"}


@pytest.mark.parametrize("value_type", [pytest.param(str, id="str"), pytest.param(None, id="implicit-str")])
@pytest.mark.parametrize("default", [pytest.param([], id="empty-default"), pytest.param(None, id="no-default")])
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
def test_parser_list_defaults_from_env(
    monkeypatch: MonkeyPatch,
    value_type: type[str] | None,
    default: list[str] | None,
    nargs: str | int | None,
    action: str,
    expected: list[str] | list[list[str]],
) -> None:
    monkeypatch.setenv("TOX_LABELS", "old;new")
    parser: Final[ToxParser] = ToxParser.base()
    parser.add_argument("-m", dest="labels", action=action, nargs=nargs, default=default, type=value_type)
    parser.fix_defaults()
    assert parser.parse_args([]).labels == expected


@pytest.mark.parametrize("value_type", [pytest.param(str, id="str"), pytest.param(None, id="implicit-str")])
@pytest.mark.parametrize("default", [pytest.param([], id="empty-default"), pytest.param(None, id="no-default")])
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
def test_parser_list_defaults_from_file(
    monkeypatch: MonkeyPatch,
    value_type: type[str] | None,
    default: list[str] | None,
    nargs: str | int | None,
    action: str,
    expected: list[str] | list[list[str]],
    tmp_path: Path,
) -> None:
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
            lambda s: 0,  # ruff:ignore[unused-lambda-argument]  # callback signature
        )  # pragma: no cover - the lambda will never be run


def test_parse_known_args_not_set(mocker: MockerFixture) -> None:
    mocker.patch.object(sys, "argv", ["a", "--help"])
    _, unknown = ToxParser.base().parse_known_args(None)
    assert unknown == ["--help"]


def test_parser_hint(capsys: CaptureFixture) -> None:
    parser = ToxParser.base()
    with pytest.raises(SystemExit):
        parser.parse_args("foo")
    _out, err = capsys.readouterr()
    assert err.endswith("hint: if you tried to pass arguments to a command use -- to separate them from tox ones\n")


def test_parser_unknown_secret_flag_masked(capsys: CaptureFixture) -> None:
    with pytest.raises(SystemExit):
        ToxParser.base().parse_args(["--api-token=hunter2"])
    err: Final = capsys.readouterr().err
    assert "--api-token=*******" in err
    assert "hunter2" not in err
