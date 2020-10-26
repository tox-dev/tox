from collections import OrderedDict
from pathlib import Path
from typing import Callable, Dict, Optional, Set, TypeVar

import pytest

from tox.config.main import Config
from tox.config.sets import ConfigSet
from tox.config.source.ini import IniLoader
from tox.pytest import ToxProject, ToxProjectCreator


@pytest.fixture
def empty_config(empty_project: ToxProject) -> Config:
    return empty_project.config()


def test_empty_config_root(empty_config: Config, empty_project: ToxProject) -> None:
    assert empty_config.core["tox_root"] == empty_project.path


def test_empty_config_repr(empty_config: Config, empty_project: ToxProject) -> None:
    text = repr(empty_config)
    assert str(empty_project.path) in text
    assert "config_source=ToxIni" in text


def test_empty_conf_tox_envs(empty_config: Config) -> None:
    tox_env_keys = list(empty_config)
    assert tox_env_keys == []


def test_empty_conf_get(empty_config: Config) -> None:
    result = empty_config["magic"]
    assert isinstance(result, ConfigSet)
    loaders = result["base"]
    assert len(loaders) == 1
    assert isinstance(loaders[0], IniLoader)


def test_config_some_envs(tox_project: ToxProjectCreator) -> None:
    example = """
    [tox]
    env_list = py38, py37
    [testenv]
    deps = 1
        other: 2
    [testenv:magic]
    """
    config = tox_project({"tox.ini": example}).config()
    tox_env_keys = list(config)
    assert tox_env_keys == ["py38", "py37", "other", "magic"]

    config_set = config["py38"]
    assert repr(config_set)
    assert isinstance(config_set, ConfigSet)
    assert list(config_set) == ["base"]


ConfBuilder = Callable[[str], ConfigSet]


@pytest.fixture(name="conf_builder")
def _conf_builder(tox_project: ToxProjectCreator) -> ConfBuilder:
    def _make(conf_str: str) -> ConfigSet:
        return tox_project({"tox.ini": f"[tox]\nenvlist=py39\n[testenv]\n{conf_str}"}).config()["py39"]

    return _make


def test_config_str(conf_builder: ConfBuilder) -> None:
    config_set = conf_builder("deps = 1\n    other: 2")
    config_set.add_config(keys="deps", of_type=str, default="", desc="ok")
    result = config_set["deps"]
    assert result == "1"


def test_config_path(conf_builder: ConfBuilder) -> None:
    config_set = conf_builder("path = path")
    config_set.add_config(keys="path", of_type=Path, default=Path(), desc="path")
    path_materialize = config_set["path"]
    assert path_materialize == Path("path")


def test_config_set(conf_builder: ConfBuilder) -> None:
    config_set = conf_builder("set = 1\n 2\n 3")
    config_set.add_config(keys="set", of_type=Set[int], default=set(), desc="set")
    set_materialize = config_set["set"]
    assert set_materialize == {1, 2, 3}


def test_config_optional_none(conf_builder: ConfBuilder) -> None:
    config_set = conf_builder("")
    config_set.add_config(
        keys="optional_none", of_type=Optional[int], default=None, desc="optional_none"  # type: ignore[arg-type]
    )
    optional_none = config_set["optional_none"]
    assert optional_none is None


def test_config_dict(conf_builder: ConfBuilder) -> None:
    config_set = conf_builder("dict = a=1\n  b=2\n  c=3")
    config_set.add_config(keys="dict", of_type=Dict[str, int], default=dict(), desc="dict")
    dict_val = config_set["dict"]
    assert dict_val == OrderedDict([("a", 1), ("b", 2), ("c", 3)])


def test_config_bad_type(conf_builder: ConfBuilder) -> None:
    config_set = conf_builder("crazy = something-bad")

    config_set.add_config(keys="crazy", of_type=TypeVar, default=TypeVar("V"), desc="crazy")
    with pytest.raises(TypeError) as context:
        assert config_set["crazy"]
    assert str(context.value) == f"something-bad cannot cast to {TypeVar!r}"


def test_config_bad_dict(conf_builder: ConfBuilder) -> None:
    config_set = conf_builder("bad_dict = something")

    config_set.add_config(keys="bad_dict", of_type=Dict[str, str], default={}, desc="bad_dict")
    with pytest.raises(TypeError) as context:
        assert config_set["bad_dict"]
    assert str(context.value) == "dictionary lines must be of form key=value, found something"


def test_config_bad_bool(conf_builder: ConfBuilder) -> None:
    config_set = conf_builder("bad_bool = whatever")
    config_set.add_config(keys="bad_bool", of_type=bool, default=False, desc="bad_bool")
    with pytest.raises(TypeError) as context:
        assert config_set["bad_bool"]
    error = "value whatever cannot be transformed to bool, valid: , 0, 1, false, no, off, on, true, yes"
    assert str(context.value) == error


def test_config_constant(conf_builder: ConfBuilder) -> None:
    config_set = conf_builder("")
    config_set.add_constant(keys="a", value=1, desc="ok")
    const = config_set["a"]
    assert const == 1


def test_config_lazy_constant(conf_builder: ConfBuilder) -> None:
    config_set = conf_builder("")
    config_set.add_constant(keys="b", value=lambda: 2, desc="ok")
    lazy_const = config_set["b"]
    assert lazy_const == 2


def test_config_constant_repr(conf_builder: ConfBuilder) -> None:
    config_set = conf_builder("")
    defined = config_set.add_constant(keys="a", value=1, desc="ok")
    assert repr(defined)


def test_config_dynamic_repr(conf_builder: ConfBuilder) -> None:
    config_set = conf_builder("path = path")
    defined = config_set.add_config(keys="path", of_type=Path, default=Path(), desc="path")
    assert repr(defined)
