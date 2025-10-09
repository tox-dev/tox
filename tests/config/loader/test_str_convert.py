from __future__ import annotations

import importlib
import sys
from pathlib import Path
from textwrap import dedent
from types import ModuleType
from typing import TYPE_CHECKING, Any, Optional, TypeVar, Union

import pytest

from tox.config.loader.str_convert import StrConvert
from tox.config.types import Command, EnvList

if TYPE_CHECKING:
    from tox.pytest import MonkeyPatch, SubRequest, ToxProjectCreator

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
        pytest.param("a", Command(["a"]), Command, id="str_a_to_command"),
        pytest.param("a,b", EnvList(["a", "b"]), EnvList, id="str_a_b_to_envlist"),
        pytest.param("", None, Optional[int], id="empty_to_optional_int"),  # noqa: UP045
        pytest.param("1", 1, Optional[int], id="str_1_to_optional_int"),  # noqa: UP045
        pytest.param("", None, Optional[str], id="empty_to_optional_str"),  # noqa: UP045
        pytest.param("1", "1", Optional[str], id="str_1_to_optional_str"),  # noqa: UP045
        pytest.param("", None, Optional[list[str]], id="empty_to_optional_list_str"),  # noqa: UP045
        pytest.param("1,2", ["1", "2"], Optional[list[str]], id="str_1_2_to_optional_list_str"),  # noqa: UP045
        pytest.param("", None, int | None, id="empty_to_int_or_none"),
        pytest.param("1", 1, int | None, id="str_1_to_int_or_none"),
        pytest.param("", None, str | None, id="empty_to_str_or_none"),
        pytest.param("1", "1", str | None, id="str_1_to_str_or_none"),
        pytest.param("", None, list[str] | None, id="empty_to_list_str_or_none"),
        pytest.param("1,2", ["1", "2"], list[str] | None, id="str_1_2_to_list_str_or_none"),
        pytest.param("1", "1", Literal["1", "2"], id="str_1_to_literal_1_2"),
    ],
)
def test_str_convert_ok(raw: str, value: Any, of_type: type[Any]) -> None:
    result = StrConvert().to(raw, of_type, None)
    assert result == value


@pytest.mark.parametrize(
    ("raw", "of_type", "exc_type", "msg"),
    [
        pytest.param("a", TypeVar, TypeError, r"a cannot cast to .*typing.TypeVar.*", id="fail_typevar"),
        pytest.param("3", Literal["1", "2"], ValueError, r"3 must be one of \('1', '2'\)", id="fail_literal_1_2"),
        pytest.param(
            "3",
            Union[str, int],  # noqa: UP007
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
    result = StrConvert().to_command(value)
    assert result is not None
    assert result.args == expected


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
    class _SelectiveSys(ModuleType):
        """A sys-like proxy that only overrides `platform`."""

        def __init__(self, patched_platform: str) -> None:
            super().__init__("sys")
            self.__dict__["_real"] = sys
            self.__dict__["_patched_platform"] = patched_platform

        def __getattr__(self, name: str) -> Any:
            if name == "platform":
                return self.__dict__["_patched_platform"]
            return getattr(self.__dict__["_real"], name)

    # Patches sys.platform only for the tox.config.loader.str_convert module.
    # Everywhere else, sys.platform remains the real value.
    mod = importlib.import_module("tox.config.loader.str_convert")
    proxy = _SelectiveSys(str(request.param))
    monkeypatch.setattr(mod, "sys", proxy, raising=True)
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
    result = StrConvert().to_command(value)
    assert result is not None
    assert result.args == expected


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
