from collections import OrderedDict
from pathlib import Path
from typing import Callable, Dict, Optional, Set, TypeVar

import pytest

from tests.conftest import ToxIniCreator
from tox.config.sets import ConfigSet

ConfBuilder = Callable[[str], ConfigSet]


@pytest.fixture(name="conf_builder")
def _conf_builder(tox_ini_conf: ToxIniCreator) -> ConfBuilder:
    def _make(conf_str: str) -> ConfigSet:
        return tox_ini_conf(f"[tox]\nenvlist=py39\n[testenv]\n{conf_str}").get_env("py39")

    return _make


def test_config_str(conf_builder: ConfBuilder) -> None:
    config_set = conf_builder("deps-x = 1\n    other: 2")
    config_set.add_config(keys="deps-x", of_type=str, default="", desc="ok")
    result = config_set["deps-x"]
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


def test_config_redefine_constant_fail(conf_builder: ConfBuilder) -> None:
    config_set = conf_builder("path = path")
    config_set.add_constant(keys="path", desc="desc", value="value")
    with pytest.raises(ValueError, match="config path already defined"):
        config_set.add_constant(keys="path", desc="desc", value="value")


def test_config_redefine_dynamic_fail(conf_builder: ConfBuilder) -> None:
    config_set = conf_builder("path = path")
    config_set.add_config(keys="path", of_type=str, default="default", desc="path")
    with pytest.raises(ValueError, match="config path already defined"):
        config_set.add_config(keys="path", of_type=str, default="default", desc="path")


def test_config_dynamic_not_equal(conf_builder: ConfBuilder) -> None:
    config_set = conf_builder("")
    path = config_set.add_config(keys="path", of_type=Path, default=Path(), desc="path")
    paths = config_set.add_config(keys="paths", of_type=Path, default=Path(), desc="path")
    assert path != paths
