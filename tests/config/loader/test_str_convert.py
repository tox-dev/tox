from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Optional, TypeVar, Union

import pytest

from tox.config.loader.str_convert import StrConvert
from tox.config.types import Command, EnvList

if TYPE_CHECKING:
    from typing import Final

    from pytest_mock import MockerFixture

    from tox.pytest import MonkeyPatch, SubRequest, ToxProject, ToxProjectCreator, ToxRunOutcome

from typing import Literal


@pytest.mark.parametrize(
    ("raw", "value", "of_type"),
    [
        pytest.param("true", True, bool, id="str_true_to_bool"),
        pytest.param("false", False, bool, id="str_false_to_bool"),
        pytest.param("True", True, bool, id="str_True_to_bool"),
        pytest.param("False", False, bool, id="str_False_to_bool"),
        pytest.param("TruE", True, bool, id="str_TruE_to_bool"),
        pytest.param("FalsE", False, bool, id="str_FalsE_to_bool"),
        pytest.param("1", True, bool, id="str_1_to_bool"),
        pytest.param("0", False, bool, id="str_0_to_bool"),
        pytest.param("1", 1, int, id="str_1_to_int"),
        pytest.param("0", 0, int, id="str_0_to_int"),
        pytest.param("+1", 1, int, id="str_plus1_to_int"),
        pytest.param("-1", -1, int, id="str_minus1_to_int"),
        pytest.param("1.1", 1.1, float, id="str_1.1_to_float"),
        pytest.param("0.1", 0.1, float, id="str_0.1_to_float"),
        pytest.param("+1.1", 1.1, float, id="str_plus1.1_to_float"),
        pytest.param("-1.1", -1.1, float, id="str_minus1.1_to_float"),
        pytest.param("magic", "magic", str, id="str_magic_to_str"),
        pytest.param("1", {"1"}, set[str], id="str_1_to_set_str"),
        pytest.param("1", [1], list[int], id="str_1_to_list_int"),
        pytest.param("1=2", {1: 2}, dict[int, int], id="str_1eq2_to_dict_int_int"),
        pytest.param("a=1\n\nc=2", {"a": 1, "c": 2}, dict[str, int], id="str_multiline_dict_str_int"),
        pytest.param("a", Path("a"), Path, id="str_a_to_path"),
        pytest.param(" path ", Path(" path "), Path, id="str_spaced_to_path"),
        pytest.param("a", Command(["a"]), Command, id="str_a_to_command"),
        pytest.param("a,b", EnvList(["a", "b"]), EnvList, id="str_a_b_to_envlist"),
        pytest.param("", None, Optional[int], id="empty_to_optional_int"),  # ruff:ignore[non-pep604-annotation-optional]
        pytest.param("1", 1, Optional[int], id="str_1_to_optional_int"),  # ruff:ignore[non-pep604-annotation-optional]
        pytest.param("", None, Optional[str], id="empty_to_optional_str"),  # ruff:ignore[non-pep604-annotation-optional]
        pytest.param("1", "1", Optional[str], id="str_1_to_optional_str"),  # ruff:ignore[non-pep604-annotation-optional]
        pytest.param("", None, Optional[list[str]], id="empty_to_optional_list_str"),  # ruff:ignore[non-pep604-annotation-optional]
        pytest.param("1,2", ["1", "2"], Optional[list[str]], id="str_1_2_to_optional_list_str"),  # ruff:ignore[non-pep604-annotation-optional]
        pytest.param("", None, int | None, id="empty_to_int_or_none"),
        pytest.param("1", 1, int | None, id="str_1_to_int_or_none"),
        pytest.param("", None, str | None, id="empty_to_str_or_none"),
        pytest.param("", None, Path | None, id="empty_to_path_or_none"),
        pytest.param("1", "1", str | None, id="str_1_to_str_or_none"),
        pytest.param("", None, list[str] | None, id="empty_to_list_str_or_none"),
        pytest.param("1,2", ["1", "2"], list[str] | None, id="str_1_2_to_list_str_or_none"),
        pytest.param("1", "1", Literal["1", "2"], id="str_1_to_literal_1_2"),
    ],
)
def test_str_convert_ok(
    raw: str,
    value: bool | float | str | set[str] | list[int | str] | dict[str | int, int] | Path | Command | EnvList | None,
    of_type: type,
) -> None:
    result = StrConvert().to(raw, of_type, None)
    assert result == value


@pytest.mark.parametrize(
    ("raw", "of_type", "exc_type", "msg"),
    [
        pytest.param("a", TypeVar, TypeError, r"a cannot cast to .*typing.TypeVar.*", id="fail_typevar"),
        pytest.param("3", Literal["1", "2"], ValueError, r"3 must be one of \('1', '2'\)", id="fail_literal_1_2"),
        pytest.param(
            "3",
            Union[str, int],  # ruff:ignore[non-pep604-annotation-union]  # tests Union spelling
            TypeError,
            r"3 cannot cast to (typing.Union\[str, int\]|str \| int)",
            id="fail_union_str_int",
        ),
        pytest.param(
            "3",
            str | int,
            TypeError,
            r"3 cannot cast to (typing.Union\[str, int\]|str \| int)",
            id="fail_union_bar_str_int",
        ),
        pytest.param("", Command, ValueError, r"attempting to parse '' into a command failed", id="fail_empty_command"),
        pytest.param("", Path, ValueError, r"path value is empty", id="fail_empty_path"),
        pytest.param("  ", Path, ValueError, r"path value is empty", id="fail_blank_path"),
    ],
)
def test_str_convert_nok(raw: str, of_type: type, msg: str, exc_type: type[Exception]) -> None:
    with pytest.raises(exc_type, match=msg):
        StrConvert().to(raw, of_type, None)


@pytest.mark.parametrize(
    "config_files",
    [
        pytest.param(
            {
                "tox.ini": (
                    "[tox]\nno_package = true\n[testenv]\n"
                    "env_tmp_dir = {env:SCRATCH_DIR}\n"
                    "commands = python -c 'print(1)'\n"
                ),
            },
            id="ini",
        ),
        pytest.param(
            {
                "tox.toml": (
                    'no_package = true\n[env_run_base]\nenv_tmp_dir = "{env:SCRATCH_DIR}"\n'
                    'commands = [["python", "-c", "print(1)"]]\n'
                ),
            },
            id="toml",
        ),
    ],
)
def test_unset_env_path_does_not_resolve_to_cwd(
    tox_project: ToxProjectCreator, monkeypatch: MonkeyPatch, config_files: dict[str, str]
) -> None:
    monkeypatch.delenv("SCRATCH_DIR", raising=False)
    project: Final[ToxProject] = tox_project({**config_files, "keep.txt": "precious"})
    outcome: Final[ToxRunOutcome] = project.run("r", "-e", "py")
    outcome.assert_failed()
    assert "failed to load py.env_tmp_dir: path value is empty" in outcome.out
    assert (project.path / "keep.txt").read_text() == "precious"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param("python ' ok", ["python", "' ok"], id="python-space-quote-space-ok-python-quote-space-ok"),
        pytest.param('python " ok', ["python", '" ok'], id="python-space-dquote-space-ok-python-dquote-space-ok"),
    ],
)
def test_invalid_shell_expression(value: str, expected: list[str]) -> None:
    result = StrConvert().to_command(value)
    assert result is not None
    assert result.args == expected


_SIMPLE_ARGS = [
    pytest.param(
        r"foo \"bar\"", ["foo", '"bar"'], id="foo-space-backslash-dquote-bar-backslash-dquote-foo-dquote-bar-dquote"
    ),
    pytest.param(
        r"foo \'bar\'", ["foo", "'bar'"], id="foo-space-backslash-quote-bar-backslash-quote-foo-quote-bar-quote"
    ),
    pytest.param(
        "foo '\"bar baz\"'",
        ["foo", '"bar baz"'],
        id="foo-space-quote-dquote-bar-space-baz-dquote-quote-foo-dquote-bar-space-baz-dquote",
    ),
    pytest.param(
        "foo \"'bar baz'\"",
        ["foo", "'bar baz'"],
        id="foo-space-dquote-quote-bar-space-baz-quote-dquote-foo-quote-bar-space-baz-quote",
    ),
    pytest.param(r"foo \"\"", ["foo", '""'], id="foo-space-backslash-dquote-backslash-dquote-foo-dquote-dquote"),
    pytest.param(r"foo \'\'", ["foo", "''"], id="foo-space-backslash-quote-backslash-quote-foo-quote-quote"),
    pytest.param('foo "bar baz"', ["foo", "bar baz"], id="foo-space-dquote-bar-space-baz-dquote-foo-bar-space-baz"),
    pytest.param(
        'foo "bar baz"ext', ["foo", "bar bazext"], id="foo-space-dquote-bar-space-baz-dquote-ext-foo-bar-space-bazext"
    ),
    pytest.param('foo="bar baz"', ["foo=bar baz"], id="foo-equal-dquote-bar-space-baz-dquote-foo-equal-bar-space-baz"),
    pytest.param("foo 'bar baz'", ["foo", "bar baz"], id="foo-space-quote-bar-space-baz-quote-foo-bar-space-baz"),
    pytest.param(
        "foo 'bar baz'ext", ["foo", "bar bazext"], id="foo-space-quote-bar-space-baz-quote-ext-foo-bar-space-bazext"
    ),
    pytest.param("foo='bar baz'", ["foo=bar baz"], id="foo-equal-quote-bar-space-baz-quote-foo-equal-bar-space-baz"),
    pytest.param(
        r"foo=\"bar baz\"",
        ['foo="bar', 'baz"'],
        id="foo-equal-backslash-dquote-bar-space-baz-backslash-dquote-foo-equal-dquote-bar-baz-dquote",
    ),
    pytest.param(
        r'foo="bar baz\"',
        ['foo="bar baz\\"'],
        id="foo-equal-dquote-bar-space-baz-backslash-dquote-foo-equal-dquote-bar-space-baz-backslash-dquote",
    ),
    pytest.param(
        "foo='bar baz' quuc",
        ["foo=bar baz", "quuc"],
        id="foo-equal-quote-bar-space-baz-quote-space-quuc-foo-equal-bar-space-baz-quuc",
    ),
    pytest.param(
        r"foo='bar baz\' quuc",
        ["foo=bar baz\\", "quuc"],
        id="foo-equal-quote-bar-space-baz-backslash-quote-space-quuc-foo-equal-bar-space-baz-backslash-quuc",
    ),
    pytest.param(
        r"foo=\"bar baz\' quuc",
        ['foo="bar', "baz'", "quuc"],
        id="foo-equal-backslash-dquote-bar-space-baz-backslash-quote-space-quuc-foo-equal-dquote-bar-baz-quote-quuc",
    ),
    pytest.param(
        r"foo=\\\"bar baz\"",
        ['foo=\\"bar', 'baz"'],
        id="foo-equal-backslash-backslash-backslash-dquote-bar-space-baz-backslash-dquote-foo-equal-backslash-dquote-bar-baz-dquote",
    ),
    pytest.param(
        r'foo=\\"bar baz\"',
        [r'foo=\\"bar baz\"'],
        id="foo-equal-backslash-backslash-dquote-bar-space-baz-backslash-dquote-foo-equal-backslash-backslash-dquote-bar-space-baz-backslash-dquote",
    ),
]
_NEWLINE_ARGS = [
    pytest.param(
        'foo\n"bar\nbaz"', ["foo", "bar\nbaz"], id="foo-newline-dquote-bar-newline-baz-dquote-foo-bar-newline-baz"
    ),
]
_INI_CONFIG_NEWLINE_ARGS = [
    pytest.param(
        'foo\\\n    "bar\\\n    baz"',
        ["foobarbaz"],
        id="foo-backslash-newline-space-space-space-space-dquote-bar-backslash-newline-space-space-space-space-baz-dquote-foobarbaz",
    ),  # behavior change from tox 3
    pytest.param(
        'foo\\\n    "bar \\\n    baz"',
        ["foobar baz"],
        id="foo-backslash-newline-space-space-space-space-dquote-bar-space-backslash-newline-space-space-space-space-baz-dquote-foobar-space-baz",
    ),  # behavior change from tox 3
    pytest.param(
        'foo \\\n    "bar\\\n    baz"',
        ["foo", "barbaz"],
        id="foo-space-backslash-newline-space-space-space-space-dquote-bar-backslash-newline-space-space-space-space-baz-dquote-foo-barbaz",
    ),
    pytest.param(
        'foo \\\n    "bar \\\n    baz"',
        ["foo", "bar baz"],
        id="foo-space-backslash-newline-space-space-space-space-dquote-bar-space-backslash-newline-space-space-space-space-baz-dquote-foo-bar-space-baz",
    ),
    pytest.param(
        'foo \\\n    \\"bar \\\n    baz"',
        ["foo", '"bar', 'baz"'],
        id="foo-space-backslash-newline-space-space-space-space-backslash-dquote-bar-space-backslash-newline-space-space-space-space-baz-dquote-foo-dquote-bar-baz-dquote",
    ),
    pytest.param(
        "foo \\\n    bar \\\n    baz",
        ["foo", "bar", "baz"],
        id="foo-space-backslash-newline-space-space-space-space-bar-space-backslash-newline-space-space-space-space-baz-foo-bar-baz",
    ),
]
_WINDOWS_PATH_ARGS = [
    pytest.param(
        r"SPECIAL:\foo\bar --quuz='baz atan'",
        [r"SPECIAL:\foo\bar", "--quuz=baz atan"],
        id="special-colon-backslash-foo-backslash-bar-space-dash-dash-quuz-equal-quote-baz-space-atan-quote-special-colon-backslash-foo-backslash-bar-dash-dash-quuz-equal-baz-space-atan",
    ),
    pytest.param(
        r"X:\\foo\\bar --quuz='baz atan'",
        [r"X:\foo\bar", "--quuz=baz atan"],
        id="x-colon-backslash-backslash-foo-backslash-backslash-bar-space-dash-dash-quuz-equal-quote-baz-space-atan-quote-x-colon-backslash-foo-backslash-bar-dash-dash-quuz-equal-baz-space-atan",
    ),
    pytest.param(
        "/foo/bar --quuz='baz atan'",
        ["/foo/bar", "--quuz=baz atan"],
        id="slash-foo-slash-bar-space-dash-dash-quuz-equal-quote-baz-space-atan-quote-slash-foo-slash-bar-dash-dash-quuz-equal-baz-space-atan",
    ),
    pytest.param(
        'cc --arg "C:\\\\Users\\""',
        ["cc", "--arg", 'C:\\Users"'],
        id="cc-space-dash-dash-arg-space-dquote-c-colon-backslash-backslash-users-backslash-dquote-dquote-cc-dash-dash-arg-c-colon-backslash-users-dquote",
    ),
    pytest.param(
        'cc --arg "C:\\\\Users\\"',
        ["cc", "--arg", '"C:\\\\Users\\"'],
        id="cc-space-dash-dash-arg-space-dquote-c-colon-backslash-backslash-users-backslash-dquote-cc-dash-dash-arg-dquote-c-colon-backslash-backslash-users-backslash-dquote",
    ),
    pytest.param(
        'cc --arg "C:\\\\Users"',
        ["cc", "--arg", "C:\\Users"],
        id="cc-space-dash-dash-arg-space-dquote-c-colon-backslash-backslash-users-dquote-cc-dash-dash-arg-c-colon-backslash-users",
    ),
    pytest.param(
        'cc --arg \\"C:\\\\Users"',
        ["cc", "--arg", '\\"C:\\\\Users"'],
        id="cc-space-dash-dash-arg-space-backslash-dquote-c-colon-backslash-backslash-users-dquote-cc-dash-dash-arg-backslash-dquote-c-colon-backslash-backslash-users-dquote",
    ),
    pytest.param(
        'cc --arg "C:\\\\Users\\ "',
        ["cc", "--arg", "C:\\Users\\ "],
        id="cc-space-dash-dash-arg-space-dquote-c-colon-backslash-backslash-users-backslash-space-dquote-cc-dash-dash-arg-c-colon-backslash-users-backslash-space",
    ),
    pytest.param(
        'cc --arg "C:\\\\Users\\\\"',
        ["cc", "--arg", "C:\\Users\\"],
        id="cc-space-dash-dash-arg-space-dquote-c-colon-backslash-backslash-users-backslash-backslash-dquote-cc-dash-dash-arg-c-colon-backslash-users-backslash",
    ),
    pytest.param(
        'cc --arg "C:\\\\Users\\\\ "',
        ["cc", "--arg", "C:\\Users\\ "],
        id="cc-space-dash-dash-arg-space-dquote-c-colon-backslash-backslash-users-backslash-backslash-space-dquote-cc-dash-dash-arg-c-colon-backslash-users-backslash-space",
    ),
    pytest.param(
        r'cc --arg C:\\Users\\ --arg2 "SPECIAL:\Temp\f o o" --arg3="\\\\FOO\share\Path name" --arg4 SPECIAL:\Temp\ '[
            :-1
        ],
        [
            "cc",
            "--arg",
            "C:\\Users\\",
            "--arg2",
            "SPECIAL:\\Temp\\f o o",
            r"--arg3=\\FOO\share\Path name",
            "--arg4",
            "SPECIAL:\\Temp\\",
        ],
        id="quote-cc-space-dash-dash-arg-space-c-colon-backslash-backslash-backslash-backslash-users-backslash-backslash-backslash-backslash-space-dash-dash-arg2-space-dquote-special-colon-backslash-backslash-temp-backslash-backslash-f-space-o-space-o-dquote-space-dash-dash-arg3-equal-dquote-backslash-backslash-backslash-backslash-backslash-backslash-backslash-backslash-foo-backslash-backslash-share-backslash-backslash-path-space-name-dquote-space-dash-dash-arg4-space-special-colon-backslash-backslash-temp-backslash-backslash-space-quote-lbracket-colon-dash-1-rbracket-cc-dash-dash-arg-c-colon-backslash-users-backslash-dash-dash-arg2-special-colon-backslash-temp-backslash-f-space-o-space-o-dash-dash-arg3-equal-backslash-backslash-foo-backslash-share-backslash-path-space-name-dash-dash-arg4-special-colon-backslash-temp-backslash",
    ),
]
_WINDOWS_TRAILING_SEP_ARGS = [
    pytest.param(
        r"command path\to\trailing\sep\ -b foo",
        ["command", "path\\to\\trailing\\sep\\", "-b", "foo"],
        id="command-space-path-backslash-to-backslash-trailing-backslash-sep-backslash-space-dash-b-space-foo-command-path-backslash-to-backslash-trailing-backslash-sep-backslash-dash-b-foo",
    ),
]
_WACKY_SLASH_ARGS = [
    pytest.param("\\\\\\", ["\\\\\\"], id="backslash-backslash-backslash-backslash-backslash-backslash"),
    pytest.param(
        " \\'\\'\\ '",
        [" \\'\\'\\ '"],
        id="space-backslash-quote-backslash-quote-backslash-space-quote-space-backslash-quote-backslash-quote-backslash-space-quote",
    ),
    pytest.param("\\'\\'\\ ", ["'' "], id="backslash-quote-backslash-quote-backslash-space-quote-quote-space"),
    pytest.param(
        "\\'\\ \\\\", ["' \\"], id="backslash-quote-backslash-space-backslash-backslash-quote-space-backslash"
    ),
    pytest.param("\\'\\ ", ["' "], id="backslash-quote-backslash-space-quote-space"),
    pytest.param(
        '''"\\'\\"''',
        ['"\\\'\\"'],
        id="dquote-backslash-quote-backslash-dquote-dquote-backslash-quote-backslash-dquote",
    ),
    pytest.param("'\\' \\\\", ["\\", "\\"], id="quote-backslash-quote-space-backslash-backslash-backslash-backslash"),
    pytest.param(
        '"\\\\" \\\\',
        ["\\", "\\"],
        id="dquote-backslash-backslash-dquote-space-backslash-backslash-backslash-backslash",
    ),
]


@pytest.fixture(params=["win32", "linux2"])
def sys_platform(request: SubRequest, mocker: MockerFixture) -> str:
    mocker.patch("tox.config.loader.str_convert.sys", mocker.create_autospec(sys, platform=request.param))
    return str(request.param)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        *_SIMPLE_ARGS,
        *_NEWLINE_ARGS,
        *_WINDOWS_PATH_ARGS,
        *_WACKY_SLASH_ARGS,
    ],
)
def test_shlex_platform_specific(sys_platform: str, value: str, expected: list[str]) -> None:
    if sys_platform != "win32" and value.startswith("SPECIAL:"):
        # on non-windows platform, backslash is always an escape, not path separator
        expected = [exp.replace("\\", "") for exp in expected]
    wacky_slash_args_win32 = {
        " \\'\\'\\ '": ["''\\", "'"],
        "\\'\\'\\ ": ["''\\"],
        "\\'\\ \\\\": ["'\\", "\\"],
        "\\'\\ ": ["'\\"],
    }
    if sys_platform == "win32" and value in wacky_slash_args_win32:
        expected = wacky_slash_args_win32[value]
    result = StrConvert().to_command(value)
    assert result is not None
    assert result.args == expected


@pytest.mark.parametrize(("value", "expected"), _WINDOWS_TRAILING_SEP_ARGS)
def test_shlex_win32_trailing_sep(sys_platform: str, value: str, expected: list[str]) -> None:
    if sys_platform != "win32":
        pytest.skip("trailing path separator only relevant on Windows")
    result = StrConvert().to_command(value)
    assert result is not None
    assert result.args == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(r"xcopy \\server\share\file.txt .", ["xcopy", r"\\server\share\file.txt", "."], id="unc-argument"),
        pytest.param(r"\\server\share", [r"\\server\share"], id="unc-command"),
        pytest.param(
            r'copy "\\server\share\file name" .', ["copy", r"\\server\share\file name", "."], id="double-quoted"
        ),
        pytest.param(
            r"copy '\\server\share\file name' .", ["copy", r"\\server\share\file name", "."], id="single-quoted"
        ),
        pytest.param(r'copy --source="\\server\share"', ["copy", r"--source=\\server\share"], id="quoted-option"),
        pytest.param(r"copy --source=\\server\share", ["copy", r"--source=\\server\share"], id="unquoted-option"),
        pytest.param(r"copy \\?\C:\file .", ["copy", r"\\?\C:\file", "."], id="extended-drive"),
        pytest.param(r"copy \\?\UNC\server\share .", ["copy", r"\\?\UNC\server\share", "."], id="extended-unc"),
        pytest.param(r"copy \\.\pipe\name .", ["copy", r"\\.\pipe\name", "."], id="device"),
        pytest.param(r"copy \\\\server\share .", ["copy", r"\\server\share", "."], id="escaped-prefix"),
        pytest.param("copy\t\\\\server\\share", ["copy", r"\\server\share"], id="tab-separator"),
        pytest.param(r'copy "\\" \\', ["copy", "\\", "\\"], id="bare-pairs"),
        pytest.param(r'copy "text \\server"', ["copy", r"text \server"], id="quoted-interior"),
        pytest.param(r"copy path\\part", ["copy", r"path\part"], id="interior-pair"),
    ],
)
@pytest.mark.parametrize("sys_platform", [pytest.param("win32", id="win32")], indirect=True)
@pytest.mark.usefixtures("sys_platform")
@pytest.mark.parametrize("via_config", [pytest.param(False, id="direct"), pytest.param(True, id="ini")])
def test_shlex_win32_unc_path(
    tox_project: ToxProjectCreator, value: str, expected: list[str], via_config: bool
) -> None:
    if via_config:
        outcome: Final = tox_project({"tox.ini": f"[testenv]\ncommands = {value}"}).run("c", "-k", "commands")
        outcome.assert_success()
        assert outcome.env_conf("py")["commands"] == [Command(args=expected)]
    else:
        assert StrConvert().to_command(value).args == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        *_SIMPLE_ARGS,
        *_INI_CONFIG_NEWLINE_ARGS,
        *_WINDOWS_PATH_ARGS,
        #        *WACKY_SLASH_ARGS,
    ],
)
def test_shlex_platform_specific_ini(
    tox_project: ToxProjectCreator,
    sys_platform: str,
    value: str,
    expected: list[str],
) -> None:
    if sys_platform != "win32" and value.startswith("SPECIAL:"):
        # on non-windows platform, backslash is always an escape, not path separator
        expected = [exp.replace("\\", "") for exp in expected]
    project = tox_project(
        {
            "tox.ini": dedent(
                """
                [testenv]
                commands =
                    %s""",
            )
            % value,
        },
    )
    outcome = project.run("c")
    outcome.assert_success()
    result = outcome.env_conf("py")["commands"]
    assert result == [Command(args=expected)]


def test_trailing_path_sep_does_not_merge_args(
    tox_project: ToxProjectCreator,
    sys_platform: str,
    monkeypatch: MonkeyPatch,
) -> None:
    if sys_platform != "win32":
        pytest.skip("trailing path separator only relevant on Windows")
    monkeypatch.setattr("os.sep", "\\")
    project = tox_project({
        "tox.ini": "[testenv]\ncommands = command path{/}to{/}sep{/} -b foo",
    })
    outcome = project.run("c")
    outcome.assert_success()
    result = outcome.env_conf("py")["commands"]
    assert result == [Command(args=["command", "path\\to\\sep\\", "-b", "foo"])]
