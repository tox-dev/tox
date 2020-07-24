from collections import OrderedDict
from pathlib import Path
from typing import Dict, Optional, Set, TypeVar

import pytest

from tox.config.main import Config
from tox.config.sets import ConfigSet
from tox.config.source.ini import IniLoader
from tox.pytest import ToxProject, ToxProjectCreator


@pytest.fixture
def emtpy_project(tox_project: ToxProjectCreator) -> ToxProject:
    return tox_project({"tox.ini": ""})


@pytest.fixture
def emtpy_config(emtpy_project: ToxProject) -> Config:
    return emtpy_project.config()


def test_empty_config_root(emtpy_config, emtpy_project):
    assert emtpy_config.core["tox_root"] == emtpy_project.path


def test_empty_config_repr(emtpy_config, emtpy_project):
    text = repr(emtpy_config)
    assert str(emtpy_project.path) in text
    assert "config_source=Ini" in text


def test_empty_conf_tox_envs(emtpy_config):
    tox_env_keys = list(emtpy_config)
    assert tox_env_keys == []


def test_empty_conf_get(emtpy_config):
    result = emtpy_config["magic"]
    assert isinstance(result, ConfigSet)
    loaders = result["base"]
    assert len(loaders) == 1
    assert isinstance(loaders[0], IniLoader)


def test_config_some_envs(tox_project: ToxProjectCreator):
    project = tox_project(
        {
            "tox.ini": """
    [tox]
    env_list = py38, py37
    [testenv]
    deps = 1
        other: 2
    path = path
    set = 1,2,3
    optional_none =
    dict =
        a=1
        b=2
        c=3
    bad_dict =
        something
    bad_bool = whatever
    crazy = something-bad
    [testenv:magic]
    """,
        },
    )
    config = project.config()
    tox_env_keys = list(config)
    assert tox_env_keys == ["py38", "py37", "other", "magic"]

    config_set = config["py37"]
    assert repr(config_set)
    assert isinstance(config_set, ConfigSet)
    assert list(config_set) == ["base"]

    config_set.add_config(keys="deps", of_type=str, default="", desc="ok")
    dynamic_materialize = config_set["deps"]
    assert dynamic_materialize == "1"

    config_set.add_config(keys="path", of_type=Path, default=Path(), desc="path")
    path_materialize = config_set["path"]
    assert path_materialize == Path("path")

    config_set.add_config(keys="set", of_type=Set[int], default=set(), desc="set")
    set_materialize = config_set["set"]
    assert set_materialize == {1, 2, 3}

    config_set.add_config(keys="optional_none", of_type=Optional[int], default=1, desc="set")
    optional_none = config_set["optional_none"]
    assert optional_none is None

    config_set.add_config(keys="dict", of_type=Dict[str, int], default=dict(), desc="dict")
    dict_val = config_set["dict"]
    assert dict_val == OrderedDict([("a", 1), ("b", 2), ("c", 3)])

    config_set.add_config(keys="crazy", of_type=TypeVar, default="1", desc="crazy")
    with pytest.raises(TypeError) as context:
        assert config_set["crazy"]
    assert str(context.value) == f"something-bad cannot cast to {TypeVar!r}"

    config_set.add_config(keys="bad_dict", of_type=Dict[str, str], default={}, desc="bad_dict")
    with pytest.raises(TypeError) as context:
        assert config_set["bad_dict"]
    assert str(context.value) == "dictionary lines must be of form key=value, found something"

    config_set.add_config(keys="bad_bool", of_type=bool, default=False, desc="bad_bool")
    with pytest.raises(TypeError) as context:
        assert config_set["bad_bool"]
    error = "value whatever cannot be transformed to bool, valid: 0, 1, false, no, off, on, true, yes"
    assert str(context.value) == error

    config_set.add_constant(keys="a", value=1, desc="ok")
    const = config_set["a"]
    assert const == 1

    config_set.add_constant(keys="b", value=lambda: 2, desc="ok")
    lazy_const = config_set["b"]
    assert lazy_const == 2

    for defined in config_set._defined.values():
        assert repr(defined)
