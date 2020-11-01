import sys

import pytest

from tests.config.loader.ini.replace.conftest import ReplaceOne


def test_replace_pos_args_none_sys_argv(replace_one: ReplaceOne) -> None:
    result = replace_one("{posargs}", None)
    assert result == ""


def test_replace_pos_args_empty_sys_argv(replace_one: ReplaceOne) -> None:
    result = replace_one("{posargs}", None)
    assert result == ""


def test_replace_pos_args_extra_sys_argv(replace_one: ReplaceOne) -> None:
    result = replace_one("{posargs}", [sys.executable, "magic"])
    assert result == f"{sys.executable} magic"


def test_replace_pos_args(replace_one: ReplaceOne) -> None:
    result = replace_one("{posargs}", ["ok", "what", " yes "])
    quote = '"' if sys.platform == "win32" else "'"
    assert result == f"ok what {quote} yes {quote}"


@pytest.mark.parametrize(
    ["value", "result"],
    [
        ("magic", "magic"),
        ("magic:colon", "magic:colon"),
        ("magic\n b:c", "magic\nb:c"),  # unescaped newline keeps the newline
        ("magi\\\n c:d", "magic:d"),  # escaped newline merges the lines
        ("\\{a\\}", "{a}"),  # escaped curly braces
    ],
)
def test_replace_pos_args_default(replace_one: ReplaceOne, value: str, result: str) -> None:
    """If we have a factor that is not specified within the core env-list then that's also an environment"""
    outcome = replace_one(f"{{posargs:{value}}}", None)
    assert result == outcome


@pytest.mark.parametrize(
    "value",
    [
        "\\{posargs}",
        "{posargs\\}",
        "\\{posargs\\}",
        "{\\{posargs}",
        "{\\{posargs}{}",
    ],
)
def test_replace_pos_args_escaped(replace_one: ReplaceOne, value: str) -> None:
    result = replace_one(value, None)
    outcome = value.replace("\\{", "{").replace("\\}", "}")
    assert result == outcome
