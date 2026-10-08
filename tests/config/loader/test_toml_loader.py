from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, TypeVar

import pytest

from tox.config.loader.api import ConfigLoadArgs
from tox.config.loader.toml import TomlLoader
from tox.config.source.toml_pyproject import TomlPyProjectSection
from tox.config.types import Command, EnvList
from tox.report import HandledError

if TYPE_CHECKING:
    from types import UnionType


def test_toml_loader_load_raw() -> None:
    loader = TomlLoader(TomlPyProjectSection.from_key("tox.env.A"), [], {"a": 1, "c": False}, {}, set())
    assert loader.load_raw("a", None, "A") == 1


def test_toml_loader_load_repr() -> None:
    loader = TomlLoader(TomlPyProjectSection.from_key("tox.env.A"), [], {"a": 1}, {}, set())
    assert repr(loader) == "TomlLoader(env.A, {'a': 1})"


def test_toml_loader_found_keys() -> None:
    loader = TomlLoader(TomlPyProjectSection.from_key("tox.env.A"), [], {"a": 1, "c": False}, {}, set())
    assert loader.found_keys() == {"a", "c"}


V = TypeVar("V")


def factory_na(obj: object) -> V:
    raise NotImplementedError


def perform_load(value: Any, of_type: type[V] | UnionType) -> V:
    env_name, key = "A", "k"
    loader = TomlLoader(TomlPyProjectSection.from_key(f"tox.env.{env_name}"), [], {key: value}, {}, set())
    args = ConfigLoadArgs(None, env_name, env_name)
    return loader.load(key, of_type, factory_na, None, args)


_PREFIX = r"failed to load A\.k: "


@pytest.mark.parametrize(
    ("value", "of_type", "expected"),
    [
        pytest.param("s", str, "s", id="str"),
        pytest.param(True, bool, True, id="bool"),
        pytest.param(["a"], list[str], ["a"], id="list"),
        pytest.param({"a": "1"}, dict[str, str], {"a": "1"}, id="dict"),
        pytest.param("/w", Path, Path("/w"), id="path"),
        pytest.param(["a", None], list[str | None], ["a", None], id="list_optional"),
        pytest.param(["a", "b"], list[Literal["a", "b"]], ["a", "b"], id="list_literal"),
    ],
)
def test_toml_loader_ok(value: Any, of_type: type[Any] | UnionType, expected: object) -> None:
    result = perform_load(value, of_type)
    assert result == expected
    assert isinstance(result, type(expected))


@pytest.mark.parametrize(
    ("value", "of_type", "msg"),
    [
        pytest.param(1, str, r"1 is not of type 'str'", id="str"),
        pytest.param("true", bool, r"'true' is not of type 'bool'", id="bool"),
        pytest.param({}, list[str], r"\{\} is not list", id="list"),
        pytest.param(["a", 2], list[str], r"2 is not of type 'str'", id="list_element"),
        pytest.param({"a"}, dict[str, str], r"\{'a'\} is not dictionary", id="dict"),
        pytest.param({"a": 1, 1: "2"}, dict[str, int], r"1 is not of type 'str'", id="dict_key"),
        pytest.param({"a": 1, "b": "2"}, dict[str, int], r"'2' is not of type 'int'", id="dict_value"),
        pytest.param(1, Path, r"1 is not of type 'str'", id="path"),
        pytest.param([["a", 1]], list[Command], r"1 is not of type 'str'", id="command"),
        pytest.param(["a", None, 1], list[str | None], r"1 is not union of str, NoneType", id="list_optional"),
        pytest.param(["a", "c"], list[Literal["a", "b"]], r"'c' is not one of literal 'a','b'", id="list_literal"),
    ],
)
def test_toml_loader_nok(value: Any, of_type: type[Any] | UnionType, msg: str) -> None:
    with pytest.raises(HandledError, match=_PREFIX + msg):
        perform_load(value, of_type)


def test_toml_loader_command_ok() -> None:
    commands = perform_load([["a", "b"], ["c"]], list[Command])
    assert isinstance(commands, list)
    assert len(commands) == 2
    assert all(isinstance(i, Command) for i in commands)

    assert commands[0].args == ["a", "b"]
    assert commands[1].args == ["c"]


def test_toml_loader_command_list_drops_empty() -> None:
    commands = perform_load([[], ["c"]], list[Command])
    assert [i.args for i in commands] == [["c"]]


def test_toml_loader_command_empty_nok() -> None:
    with pytest.raises(HandledError, match=_PREFIX + r"attempting to parse \[\] into a command failed"):
        perform_load([], Command)


def test_toml_loader_env_list_ok() -> None:
    res = perform_load(["a", "b"], EnvList)
    assert isinstance(res, EnvList)
    assert list(res) == ["a", "b"]


def test_toml_loader_env_list_nok() -> None:
    with pytest.raises(
        HandledError,
        match=_PREFIX + r"env_list items must be strings, product dicts, range dicts, or labeled dicts, got int",
    ):
        perform_load(["a", 1], EnvList)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        pytest.param(
            [{"prefix": "py3", "start": 12, "stop": 14}],
            ["py312", "py313", "py314"],
            id="bare-range",
        ),
        pytest.param(
            ["lint", {"prefix": "py3", "start": 12, "stop": 13}, "docs"],
            ["lint", "py312", "py313", "docs"],
            id="mixed-literal-and-range",
        ),
        pytest.param(
            [{"ecosystem": ["oci", "python"]}],
            ["oci", "python"],
            id="bare-labeled",
        ),
        pytest.param(
            [
                {"prefix": "py3", "start": 12, "stop": 13},
                {"product": [["min"], {"prefix": "py3", "start": 12, "stop": 13}]},
            ],
            ["py312", "py313", "min-py312", "min-py313"],
            id="bare-range-plus-product",
        ),
    ],
)
def test_toml_loader_env_list_shorthand(raw: list[Any], expected: list[str]) -> None:
    res = perform_load(raw, EnvList)
    assert isinstance(res, EnvList)
    assert list(res) == expected


def test_toml_loader_env_list_prefix_and_product_rejected() -> None:
    with pytest.raises(HandledError, match=_PREFIX + r"env_list dict items cannot combine 'product' with 'prefix'"):
        perform_load([{"prefix": "py3", "product": [["a"]]}], EnvList)


def test_toml_loader_env_list_nested_dict_in_list_rejects_with_hint() -> None:
    with pytest.raises(
        HandledError,
        match=_PREFIX + r"factor group list items must be strings, got dict.*sibling factor groups",
    ):
        perform_load([{"product": [[{"prefix": "py3", "start": 9, "stop": 14}]]}], EnvList)


def test_toml_loader_union_list_or_str_with_list() -> None:
    assert perform_load(["a", "b"], list[str] | str) == ["a", "b"]


def test_toml_loader_union_list_or_str_with_str() -> None:
    assert perform_load("a", list[str] | str) == "a"


def test_toml_loader_dict_of_env_list_values_ok() -> None:
    res = perform_load(
        {
            "x": ["a", "b"],
            "y": [{"product": [["a", "b"], ["1", "2"]]}],
            "z": [{"product": [["a", "b"], {"prefix": "f", "start": 1, "stop": 2}]}],
        },
        dict[str, EnvList],
    )
    assert isinstance(res, dict)
    assert all(isinstance(v, EnvList) for v in res.values())
    assert list(res["x"]) == ["a", "b"]
    assert list(res["y"]) == ["a-1", "a-2", "b-1", "b-2"]
    assert list(res["z"]) == ["a-f1", "a-f2", "b-f1", "b-f2"]


def test_toml_loader_dict_of_env_list_values_nok() -> None:
    with pytest.raises(
        HandledError,
        match=_PREFIX + r"env_list items must be strings, product dicts, range dicts, or labeled dicts, got int",
    ):
        perform_load({"x": ["a", 1]}, dict[str, EnvList])


def test_toml_loader_list_of_env_list_ok() -> None:
    res = perform_load(
        [
            ["a", "b"],
            [{"product": [["a", "b"], ["1", "2"]]}],
            [{"product": [["a", "b"], {"prefix": "f", "start": 1, "stop": 2}]}],
        ],
        list[EnvList],
    )
    assert isinstance(res, list)
    assert all(isinstance(v, EnvList) for v in res)
    assert list(res[0]) == ["a", "b"]
    assert list(res[1]) == ["a-1", "a-2", "b-1", "b-2"]
    assert list(res[2]) == ["a-f1", "a-f2", "b-f1", "b-f2"]


def test_toml_loader_list_of_env_list_nok() -> None:
    with pytest.raises(HandledError, match=_PREFIX + r"env_list must be a list, got str"):
        perform_load(["a"], list[EnvList])
