from __future__ import annotations

import math
from pathlib import Path, PurePosixPath

import pytest

from tox.config.loader.native import to_native
from tox.config.set_env import SetEnv
from tox.config.types import Command, EnvList
from tox.tox_env.python.pip.req_file import PythonDeps


def test_str() -> None:
    assert to_native("hello") == "hello"


def test_bool_true() -> None:
    assert to_native(True) is True


def test_bool_false() -> None:
    assert to_native(False) is False


def test_bool_before_int() -> None:
    result = to_native(True)
    assert result is True
    assert not isinstance(result, int) or isinstance(result, bool)


def test_int() -> None:
    assert to_native(42) == 42


def test_float() -> None:
    assert to_native(math.pi) == math.pi


def test_path(tmp_path: Path) -> None:
    assert to_native(tmp_path) == str(tmp_path)


def test_posix_path() -> None:
    assert to_native(PurePosixPath("/usr/bin")) == "/usr/bin"


def test_dict() -> None:
    assert to_native({"a": 1, "b": "c"}) == {"a": 1, "b": "c"}


def test_nested_dict() -> None:
    assert to_native({"a": {"b": 1}}) == {"a": {"b": 1}}


def test_list() -> None:
    assert to_native([1, "two", 3.0]) == [1, "two", 3.0]


def test_list_of_paths(tmp_path: Path) -> None:
    p = tmp_path / "a"
    assert to_native([p]) == [str(p)]


def test_set() -> None:
    result = to_native({"c", "a", "b"})
    assert result == ["a", "b", "c"]


def test_env_list() -> None:
    assert to_native(EnvList(["py39", "py310", "lint"])) == ["py39", "py310", "lint"]


def test_command_simple() -> None:
    assert to_native(Command(["pytest"])) == "pytest"


@pytest.mark.parametrize(
    ("args", "expected_prefix"),
    [
        (["pytest", "-v"], "pytest"),
        (["-", "cmd"], "cmd"),
        (["!", "cmd"], "cmd"),
    ],
)
def test_command_variants(args: list[str], expected_prefix: str) -> None:
    result = to_native(Command(args))
    assert isinstance(result, str)
    assert expected_prefix in result


def test_set_env(tmp_path: Path) -> None:
    raw = "A=1\nB=hello"
    se = SetEnv(raw, "set_env", "py", tmp_path)
    result = to_native(se)
    assert result == {"A": "1", "B": "hello"}


def test_python_deps(tmp_path: Path) -> None:
    (tmp_path / "tox.ini").touch()
    deps = PythonDeps("pytest\nflask>=2.0", tmp_path)
    result = to_native(deps)
    assert result == ["pytest", "flask>=2.0"]


def test_fallback_unknown_type() -> None:
    class Custom:
        def __str__(self) -> str:
            return "custom-value"

    assert to_native(Custom()) == "custom-value"


def test_empty_str() -> None:
    assert to_native("") is not None
    assert isinstance(to_native(""), str)
    assert len(to_native("")) == 0


def test_zero() -> None:
    assert to_native(0) == 0
    assert isinstance(to_native(0), int)


def test_float_zero() -> None:
    result = to_native(0.0)
    assert isinstance(result, float)
    assert result == pytest.approx(0.0)
