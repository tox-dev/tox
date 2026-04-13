from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, NoReturn, TypeVar

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


def factory_na(obj: object) -> NoReturn:
    raise NotImplementedError


V = TypeVar("V")


def perform_load(value: Any, of_type: type[V] | UnionType) -> V:
    env_name, key = "A", "k"
    loader = TomlLoader(TomlPyProjectSection.from_key(f"tox.env.{env_name}"), [], {key: value}, {}, set())
    args = ConfigLoadArgs(None, env_name, env_name)
    return loader.load(key, of_type, factory_na, None, args)


_PREFIX = r"failed to load A\.k: "


def test_toml_loader_str_ok() -> None:
    assert perform_load("s", str) == "s"


def test_toml_loader_str_nok() -> None:
    with pytest.raises(HandledError, match=_PREFIX + r"1 is not of type 'str'"):
        perform_load(1, str)


def test_toml_loader_bool_ok() -> None:
    assert perform_load(True, bool) is True


def test_toml_loader_bool_nok() -> None:
    with pytest.raises(HandledError, match=_PREFIX + r"'true' is not of type 'bool'"):
        perform_load("true", bool)


def test_toml_loader_list_ok() -> None:
    assert perform_load(["a"], list[str]) == ["a"]


def test_toml_loader_list_nok() -> None:
    with pytest.raises(HandledError, match=_PREFIX + r"\{\} is not list"):
        perform_load({}, list[str])


def test_toml_loader_list_nok_element() -> None:
    with pytest.raises(HandledError, match=_PREFIX + r"2 is not of type 'str'"):
        perform_load(["a", 2], list[str])


def test_toml_loader_dict_ok() -> None:
    assert perform_load({"a": "1"}, dict[str, str]) == {"a": "1"}


def test_toml_loader_dict_nok() -> None:
    with pytest.raises(HandledError, match=_PREFIX + r"\{'a'\} is not dictionary"):
        perform_load({"a"}, dict[str, str])


def test_toml_loader_dict_nok_key() -> None:
    with pytest.raises(HandledError, match=_PREFIX + r"1 is not of type 'str'"):
        perform_load({"a": 1, 1: "2"}, dict[str, int])


def test_toml_loader_dict_nok_value() -> None:
    with pytest.raises(HandledError, match=_PREFIX + r"'2' is not of type 'int'"):
        perform_load({"a": 1, "b": "2"}, dict[str, int])


def test_toml_loader_path_ok() -> None:
    assert perform_load("/w", Path) == Path("/w")


def test_toml_loader_path_nok() -> None:
    with pytest.raises(HandledError, match=_PREFIX + r"1 is not of type 'str'"):
        perform_load(1, Path)


def test_toml_loader_command_ok() -> None:
    commands = perform_load([["a", "b"], ["c"]], list[Command])
    assert isinstance(commands, list)
    assert len(commands) == 2
    assert all(isinstance(i, Command) for i in commands)

    assert commands[0].args == ["a", "b"]
    assert commands[1].args == ["c"]


def test_toml_loader_command_nok() -> None:
    with pytest.raises(HandledError, match=_PREFIX + r"1 is not of type 'str'"):
        perform_load([["a", 1]], list[Command])


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


def test_toml_loader_list_optional_ok() -> None:
    assert perform_load(["a", None], list[str | None]) == ["a", None]


def test_toml_loader_list_optional_nok() -> None:
    with pytest.raises(HandledError, match=_PREFIX + r"1 is not union of str, NoneType"):
        perform_load(["a", None, 1], list[str | None])


def test_toml_loader_list_literal_ok() -> None:
    assert perform_load(["a", "b"], list[Literal["a", "b"]]) == ["a", "b"]


def test_toml_loader_list_literal_nok() -> None:
    with pytest.raises(HandledError, match=_PREFIX + r"'c' is not one of literal 'a','b'"):
        perform_load(["a", "c"], list[Literal["a", "b"]])


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
