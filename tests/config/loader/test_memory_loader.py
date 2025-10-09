from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set  # noqa: UP035

import pytest

from tox.config.loader.api import ConfigLoadArgs, Override
from tox.config.loader.memory import MemoryLoader
from tox.config.types import Command, EnvList


def test_memory_loader_repr() -> None:
    loader = MemoryLoader(a=1)
    assert repr(loader) == "MemoryLoader"


def test_memory_loader_override() -> None:
    loader = MemoryLoader(a=1)
    loader.overrides["a"] = [Override("a=2")]
    args = ConfigLoadArgs([], "name", None)
    loaded = loader.load("a", of_type=int, conf=None, factory=None, args=args)
    assert loaded == 2


@pytest.mark.parametrize(
    ("value", "of_type", "outcome"),
    [
        pytest.param(True, bool, True, id="bool_true"),
        pytest.param(1, int, 1, id="int_1"),
        pytest.param("magic", str, "magic", id="str_magic"),
        pytest.param({"1"}, set[str], {"1"}, id="set_str_1"),
        pytest.param({"1"}, Set[str], {"1"}, id="set_typing_str_1"),  # noqa: UP006
        pytest.param([1], list[int], [1], id="list_int_1"),
        pytest.param([1], List[int], [1], id="list_typing_int_1"),  # noqa: UP006
        pytest.param({1: 2}, dict[int, int], {1: 2}, id="dict_int_int_1_2"),
        pytest.param({1: 2}, Dict[int, int], {1: 2}, id="dict_int_int_1_2"),  # noqa: UP006
        pytest.param(Path.cwd(), Path, Path.cwd(), id="path_cwd"),
        pytest.param(Command(["a"]), Command, Command(["a"]), id="command_a"),
        pytest.param(EnvList("a,b"), EnvList, EnvList("a,b"), id="envlist_a_b"),
        pytest.param(1, Optional[int], 1, id="optional_int_1"),  # noqa: UP045
        pytest.param("1", Optional[str], "1", id="optional_str_1"),  # noqa: UP045
        pytest.param(1, int | None, 1, id="int_or_none_1"),
        pytest.param("1", str | None, "1", id="str_or_none_1"),
        pytest.param(0, bool, False, id="bool_false_from_0"),
        pytest.param(1, bool, True, id="bool_true_from_1"),
        pytest.param("1", int, 1, id="int_from_str_1"),
        pytest.param(1, str, "1", id="str_from_int_1"),
        pytest.param({1}, set[str], {"1"}, id="set_str_from_int_1"),
        pytest.param({"1"}, list[int], [1], id="list_int_from_str_1"),
        pytest.param({"1": "2"}, dict[int, int], {1: 2}, id="dict_int_int_from_str_1_2"),
        pytest.param(os.getcwd(), Path, Path.cwd(), id="path_from_getcwd"),  # noqa: PTH109
        pytest.param("pip list", Command, Command(["pip", "list"]), id="command_pip_list"),
        pytest.param("a\nb", EnvList, EnvList(["a", "b"]), id="envlist_a_b_newline"),
        pytest.param("1", Optional[int], 1, id="optional_int_from_str_1"),  # noqa: UP045
        pytest.param("1", int | None, 1, id="int_or_none_from_str_1"),
    ],
)
def test_memory_loader(value: Any, of_type: type[Any], outcome: Any) -> None:
    loader = MemoryLoader(a=value, kwargs={})
    args = ConfigLoadArgs([], "name", None)
    loaded = loader.load("a", of_type=of_type, conf=None, factory=None, args=args)
    assert loaded == outcome


@pytest.mark.parametrize(
    ("value", "of_type", "exception", "msg"),
    [
        ("m", int, ValueError, "invalid literal for int"),
        ({"m"}, set[int], ValueError, "invalid literal for int"),
        (["m"], list[int], ValueError, "invalid literal for int"),
        ({"m": 1}, dict[int, int], ValueError, "invalid literal for int"),
        ({1: "m"}, dict[int, int], ValueError, "invalid literal for int"),
        (object, Path, TypeError, r"str(, bytes)? or (an )?os\.PathLike object"),
        (1, Command, TypeError, "1"),
        (1, EnvList, TypeError, "1"),
    ],
)
def test_memory_loader_fails_invalid(value: Any, of_type: type[Any], exception: Exception, msg: str) -> None:
    loader = MemoryLoader(a=value, kwargs={})
    args = ConfigLoadArgs([], "name", None)
    with pytest.raises(exception, match=msg):  # type: ignore[call-overload]
        loader.load("a", of_type=of_type, conf=None, factory=None, args=args)


def test_memory_found_keys() -> None:
    loader = MemoryLoader(a=1, c=2)
    assert loader.found_keys() == {"a", "c"}


def test_memory_loader_contains() -> None:
    loader = MemoryLoader(a=1)
    assert "a" in loader
    assert "b" not in loader
