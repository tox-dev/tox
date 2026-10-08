from __future__ import annotations

import math
from pathlib import Path, PurePosixPath

import pytest

from tox.config.loader.native import to_native
from tox.config.set_env import SetEnv
from tox.config.types import Command, EnvList
from tox.tox_env.python.pip.req_file import PythonDeps
from tox.util.typing_compat import override


class _Custom:
    @override
    def __str__(self) -> str:
        return "custom-value"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param("hello", "hello", id="str"),
        pytest.param("", "", id="empty_str"),
        pytest.param(True, True, id="bool_true"),
        pytest.param(False, False, id="bool_false"),
        pytest.param(42, 42, id="int"),
        pytest.param(0, 0, id="zero"),
        pytest.param(math.pi, math.pi, id="float"),
        pytest.param(0.0, 0.0, id="float_zero"),
        pytest.param(PurePosixPath("/usr/bin"), "/usr/bin", id="posix_path"),
        pytest.param({"a": 1, "b": "c"}, {"a": 1, "b": "c"}, id="dict"),
        pytest.param({"a": {"b": 1}}, {"a": {"b": 1}}, id="nested_dict"),
        pytest.param([1, "two", 3.0], [1, "two", 3.0], id="list"),
        pytest.param({"c", "a", "b"}, ["a", "b", "c"], id="set"),
        pytest.param(EnvList(["py39", "py310", "lint"]), ["py39", "py310", "lint"], id="env_list"),
        pytest.param(Command(["pytest"]), "pytest", id="command_simple"),
        pytest.param(_Custom(), "custom-value", id="fallback_unknown_type"),
    ],
)
def test_to_native(value: object, expected: object) -> None:
    result = to_native(value)
    assert result == expected
    assert isinstance(result, type(expected))


def test_path(tmp_path: Path) -> None:
    assert to_native(tmp_path) == str(tmp_path)


def test_list_of_paths(tmp_path: Path) -> None:
    p = tmp_path / "a"
    assert to_native([p]) == [str(p)]


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
