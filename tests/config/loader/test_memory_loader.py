from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

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
        (True, bool, True),
        (1, int, 1),
        ("magic", str, "magic"),
        ({"1"}, Set[str], {"1"}),
        ([1], List[int], [1]),
        ({1: 2}, Dict[int, int], {1: 2}),
        (Path.cwd(), Path, Path.cwd()),
        (Command(["a"]), Command, Command(["a"])),
        (EnvList("a,b"), EnvList, EnvList("a,b")),
        (1, Optional[int], 1),
        ("1", Optional[str], "1"),
        (0, bool, False),
        (1, bool, True),
        ("1", int, 1),
        (1, str, "1"),
        ({1}, Set[str], {"1"}),
        ({"1"}, List[int], [1]),
        ({"1": "2"}, Dict[int, int], {1: 2}),
        (os.getcwd(), Path, Path.cwd()),  # noqa: PTH109
        ("pip list", Command, Command(["pip", "list"])),
        ("a\nb", EnvList, EnvList(["a", "b"])),
        ("1", Optional[int], 1),
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
        ({"m"}, Set[int], ValueError, "invalid literal for int"),
        (["m"], List[int], ValueError, "invalid literal for int"),
        ({"m": 1}, Dict[int, int], ValueError, "invalid literal for int"),
        ({1: "m"}, Dict[int, int], ValueError, "invalid literal for int"),
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
