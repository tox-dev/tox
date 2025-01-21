from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, TypeVar

import pytest

from tox.config.loader.api import ConfigLoadArgs
from tox.config.loader.toml import TomlLoader
from tox.config.source.toml_pyproject import TomlPyProjectSection
from tox.config.types import Command, EnvList


def test_toml_loader_load_raw() -> None:
    loader = TomlLoader(TomlPyProjectSection.from_key("tox.env.A"), [], {"a": 1, "c": False}, {}, set())
    assert loader.load_raw("a", None, "A") == 1


def test_toml_loader_load_repr() -> None:
    loader = TomlLoader(TomlPyProjectSection.from_key("tox.env.A"), [], {"a": 1}, {}, set())
    assert repr(loader) == "TomlLoader(env.A, {'a': 1})"


def test_toml_loader_found_keys() -> None:
    loader = TomlLoader(TomlPyProjectSection.from_key("tox.env.A"), [], {"a": 1, "c": False}, {}, set())
    assert loader.found_keys() == {"a", "c"}


def factory_na(obj: object) -> None:
    raise NotImplementedError


V = TypeVar("V")


def perform_load(value: Any, of_type: type[V]) -> V:
    env_name, key = "A", "k"
    loader = TomlLoader(TomlPyProjectSection.from_key(f"tox.env.{env_name}"), [], {key: value}, {}, set())
    args = ConfigLoadArgs(None, env_name, env_name)
    return loader.load(key, of_type, factory_na, None, args)  # type: ignore[arg-type]


def test_toml_loader_str_ok() -> None:
    assert perform_load("s", str) == "s"


def test_toml_loader_str_nok() -> None:
    with pytest.raises(TypeError, match="1 is not of type 'str'"):
        perform_load(1, str)


def test_toml_loader_bool_ok() -> None:
    assert perform_load(True, bool) is True


def test_toml_loader_bool_nok() -> None:
    with pytest.raises(TypeError, match="'true' is not of type 'bool'"):
        perform_load("true", bool)


def test_toml_loader_list_ok() -> None:
    assert perform_load(["a"], List[str]) == ["a"]


def test_toml_loader_list_nok() -> None:
    with pytest.raises(TypeError, match=r"{} is not list"):
        perform_load({}, List[str])


def test_toml_loader_list_nok_element() -> None:
    with pytest.raises(TypeError, match="2 is not of type 'str'"):
        perform_load(["a", 2], List[str])


def test_toml_loader_dict_ok() -> None:
    assert perform_load({"a": "1"}, Dict[str, str]) == {"a": "1"}


def test_toml_loader_dict_nok() -> None:
    with pytest.raises(TypeError, match=r"{'a'} is not dictionary"):
        perform_load({"a"}, Dict[str, str])


def test_toml_loader_dict_nok_key() -> None:
    with pytest.raises(TypeError, match="1 is not of type 'str'"):
        perform_load({"a": 1, 1: "2"}, Dict[str, int])


def test_toml_loader_dict_nok_value() -> None:
    with pytest.raises(TypeError, match="'2' is not of type 'int'"):
        perform_load({"a": 1, "b": "2"}, Dict[str, int])


def test_toml_loader_path_ok() -> None:
    assert perform_load("/w", Path) == Path("/w")


def test_toml_loader_path_nok() -> None:
    with pytest.raises(TypeError, match="1 is not of type 'str'"):
        perform_load(1, Path)


def test_toml_loader_command_ok() -> None:
    commands = perform_load([["a", "b"], ["c"]], List[Command])
    assert isinstance(commands, list)
    assert len(commands) == 2
    assert all(isinstance(i, Command) for i in commands)

    assert commands[0].args == ["a", "b"]
    assert commands[1].args == ["c"]


def test_toml_loader_command_nok() -> None:
    with pytest.raises(TypeError, match="1 is not of type 'str'"):
        perform_load([["a", 1]], List[Command])


def test_toml_loader_env_list_ok() -> None:
    res = perform_load(["a", "b"], EnvList)
    assert isinstance(res, EnvList)
    assert list(res) == ["a", "b"]


def test_toml_loader_env_list_nok() -> None:
    with pytest.raises(TypeError, match="1 is not of type 'str'"):
        perform_load(["a", 1], EnvList)


def test_toml_loader_list_optional_ok() -> None:
    assert perform_load(["a", None], List[Optional[str]]) == ["a", None]


def test_toml_loader_list_optional_nok() -> None:
    with pytest.raises(TypeError, match="1 is not union of str, NoneType"):
        perform_load(["a", None, 1], List[Optional[str]])


def test_toml_loader_list_literal_ok() -> None:
    assert perform_load(["a", "b"], List[Literal["a", "b"]]) == ["a", "b"]


def test_toml_loader_list_literal_nok() -> None:
    with pytest.raises(TypeError, match="'c' is not one of literal 'a','b'"):
        perform_load(["a", "c"], List[Literal["a", "b"]])
