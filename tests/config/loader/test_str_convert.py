from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, TypeVar, Union

import pytest

from tox.config.loader.str_convert import StrConvert
from tox.config.types import Command, EnvList

if TYPE_CHECKING:
    from tox.pytest import MonkeyPatch, SubRequest, ToxProjectCreator

from typing import Literal


@pytest.mark.parametrize(
    ("raw", "value", "of_type"),
    [
        ("true", True, bool),
        ("false", False, bool),
        ("True", True, bool),
        ("False", False, bool),
        ("TruE", True, bool),
        ("FalsE", False, bool),
        ("1", True, bool),
        ("0", False, bool),
        ("1", 1, int),
        ("0", 0, int),
        ("+1", 1, int),
        ("-1", -1, int),
        ("1.1", 1.1, float),
        ("0.1", 0.1, float),
        ("+1.1", 1.1, float),
        ("-1.1", -1.1, float),
        ("magic", "magic", str),
        ("1", {"1"}, Set[str]),
        ("1", [1], List[int]),
        ("1=2", {1: 2}, Dict[int, int]),
        ("a=1\n\nc=2", {"a": 1, "c": 2}, Dict[str, int]),
        ("a", Path("a"), Path),
        ("a", Command(["a"]), Command),
        ("a,b", EnvList(["a", "b"]), EnvList),
        ("", None, Optional[int]),
        ("1", 1, Optional[int]),
        ("", None, Optional[str]),
        ("1", "1", Optional[str]),
        ("", None, Optional[List[str]]),
        ("1,2", ["1", "2"], Optional[List[str]]),
        ("1", "1", Literal["1", "2"]),
    ],
)
def test_str_convert_ok(raw: str, value: Any, of_type: type[Any]) -> None:
    result = StrConvert().to(raw, of_type, None)
    assert result == value


# Tests that can work only with py39 or newer due to type not being subscriptible before
if sys.version_info >= (3, 9):

    @pytest.mark.parametrize(
        ("raw", "value", "of_type"),
        [
            ("", None, Optional[list[str]]),
            ("1,2", ["1", "2"], Optional[list[str]]),
        ],
    )
    def test_str_convert_ok_py39(raw: str, value: Any, of_type: type[Any]) -> None:
        result = StrConvert().to(raw, of_type, None)
        assert result == value


@pytest.mark.parametrize(
    ("raw", "of_type", "exc_type", "msg"),
    [
        ("a", TypeVar, TypeError, r"a cannot cast to .*typing.TypeVar.*"),
        ("3", Literal["1", "2"], ValueError, r"3 must be one of \('1', '2'\)"),
        ("3", Union[str, int], TypeError, r"3 cannot cast to typing.Union\[str, int\]"),
        ("", Command, ValueError, r"attempting to parse '' into a command failed"),
    ],
)
def test_str_convert_nok(raw: str, of_type: type[Any], msg: str, exc_type: type[Exception]) -> None:
    with pytest.raises(exc_type, match=msg):
        StrConvert().to(raw, of_type, None)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("python ' ok", ["python", "' ok"]),
        ('python " ok', ["python", '" ok']),
    ],
)
def test_invalid_shell_expression(value: str, expected: list[str]) -> None:
    result = StrConvert().to_command(value).args
    assert result == expected


SIMPLE_ARGS = [
    ('foo "bar baz"', ["foo", "bar baz"]),
    ('foo "bar baz"ext', ["foo", "bar bazext"]),
    ('foo="bar baz"', ["foo=bar baz"]),
    ("foo 'bar baz'", ["foo", "bar baz"]),
    ("foo 'bar baz'ext", ["foo", "bar bazext"]),
    ("foo='bar baz'", ["foo=bar baz"]),
    (r"foo=\"bar baz\"", ['foo="bar', 'baz"']),
    (r'foo="bar baz\"', ['foo="bar baz\\"']),
    ("foo='bar baz' quuc", ["foo=bar baz", "quuc"]),
    (r"foo='bar baz\' quuc", ["foo=bar baz\\", "quuc"]),
    (r"foo=\"bar baz\' quuc", ['foo="bar', "baz'", "quuc"]),
    (r"foo=\\\"bar baz\"", ['foo=\\"bar', 'baz"']),
    (r'foo=\\"bar baz\"', [r'foo=\\"bar baz\"']),
]
NEWLINE_ARGS = [
    ('foo\n"bar\nbaz"', ["foo", "bar\nbaz"]),
]
INI_CONFIG_NEWLINE_ARGS = [
    ('foo\\\n    "bar\\\n    baz"', ["foobarbaz"]),  # behavior change from tox 3
    ('foo\\\n    "bar \\\n    baz"', ["foobar baz"]),  # behavior change from tox 3
    ('foo \\\n    "bar\\\n    baz"', ["foo", "barbaz"]),
    ('foo \\\n    "bar \\\n    baz"', ["foo", "bar baz"]),
    ('foo \\\n    \\"bar \\\n    baz"', ["foo", '"bar', 'baz"']),
    ("foo \\\n    bar \\\n    baz", ["foo", "bar", "baz"]),
]
WINDOWS_PATH_ARGS = [
    (r"SPECIAL:\foo\bar --quuz='baz atan'", [r"SPECIAL:\foo\bar", "--quuz=baz atan"]),
    (r"X:\\foo\\bar --quuz='baz atan'", [r"X:\foo\bar", "--quuz=baz atan"]),
    ("/foo/bar --quuz='baz atan'", ["/foo/bar", "--quuz=baz atan"]),
    ('cc --arg "C:\\\\Users\\""', ["cc", "--arg", 'C:\\Users"']),
    ('cc --arg "C:\\\\Users\\"', ["cc", "--arg", '"C:\\\\Users\\"']),
    ('cc --arg "C:\\\\Users"', ["cc", "--arg", "C:\\Users"]),
    ('cc --arg \\"C:\\\\Users"', ["cc", "--arg", '\\"C:\\\\Users"']),
    ('cc --arg "C:\\\\Users\\ "', ["cc", "--arg", "C:\\Users\\ "]),
    ('cc --arg "C:\\\\Users\\\\"', ["cc", "--arg", "C:\\Users\\"]),
    ('cc --arg "C:\\\\Users\\\\ "', ["cc", "--arg", "C:\\Users\\ "]),
    (
        r'cc --arg C:\\Users\\ --arg2 "SPECIAL:\Temp\f o o" --arg3="\\FOO\share\Path name" --arg4 SPECIAL:\Temp\ '[:-1],
        [
            "cc",
            "--arg",
            "C:\\Users\\",
            "--arg2",
            "SPECIAL:\\Temp\\f o o",
            "--arg3=\\FOO\\share\\Path name",
            "--arg4",
            "SPECIAL:\\Temp\\",
        ],
    ),
]
WACKY_SLASH_ARGS = [
    ("\\\\\\", ["\\\\\\"]),
    (" \\'\\'\\ '", [" \\'\\'\\ '"]),
    ("\\'\\'\\ ", ["'' "]),
    ("\\'\\ \\\\", ["' \\"]),
    ("\\'\\ ", ["' "]),
    ('''"\\'\\"''', ['"\\\'\\"']),
    ("'\\' \\\\", ["\\", "\\"]),
    ('"\\\\" \\\\', ["\\", "\\"]),
]


@pytest.fixture(params=["win32", "linux2"])
def sys_platform(request: SubRequest, monkeypatch: MonkeyPatch) -> str:
    monkeypatch.setattr(sys, "platform", request.param)
    return str(request.param)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        *SIMPLE_ARGS,
        *NEWLINE_ARGS,
        *WINDOWS_PATH_ARGS,
        *WACKY_SLASH_ARGS,
    ],
)
def test_shlex_platform_specific(sys_platform: str, value: str, expected: list[str]) -> None:
    if sys_platform != "win32" and value.startswith("SPECIAL:"):
        # on non-windows platform, backslash is always an escape, not path separator
        expected = [exp.replace("\\", "") for exp in expected]
    result = StrConvert().to_command(value).args
    assert result == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        *SIMPLE_ARGS,
        *INI_CONFIG_NEWLINE_ARGS,
        *WINDOWS_PATH_ARGS,
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
    env_config = outcome.env_conf("py")
    result = env_config["commands"]
    assert result == [Command(args=expected)]
