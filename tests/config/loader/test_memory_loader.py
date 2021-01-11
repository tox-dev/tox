from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type

import pytest

from tox.config.loader.api import Override
from tox.config.loader.memory import MemoryLoader
from tox.config.types import Command, EnvList


def test_memory_loader_repr() -> None:
    loader = MemoryLoader(a=1)
    assert repr(loader) == "MemoryLoader"


def test_memory_loader_override() -> None:
    loader = MemoryLoader(a=1)
    loader.overrides["a"] = Override("a=2")
    loaded = loader.load("a", of_type=int, conf=None, env_name=None, chain=[])
    assert loaded == 2


@pytest.mark.parametrize(
    ["value", "of_type"],
    [
        (True, bool),
        (1, int),
        ("magic", str),
        ({"1"}, Set[str]),
        ([1], List[int]),
        ({1: 2}, Dict[int, int]),
        (Path.cwd(), Path),
        (Command(["a"]), Command),
        (EnvList("a,b"), EnvList),
        (1, Optional[int]),
        ("1", Optional[str]),
    ],
)
def test_memory_loader(value: Any, of_type: Type[Any]) -> None:
    loader = MemoryLoader(**{"a": value})
    loaded = loader.load("a", of_type=of_type, conf=None, env_name=None, chain=[])  # noqa
    assert loaded == value


def test_memory_found_keys() -> None:
    loader = MemoryLoader(a=1, c=2)
    assert loader.found_keys() == {"a", "c"}
