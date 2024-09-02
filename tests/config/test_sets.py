from __future__ import annotations

import re
from collections import OrderedDict
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Dict, Optional, Set, TypeVar

import pytest

from tox.config.cli.parser import Parsed
from tox.config.loader.memory import MemoryLoader
from tox.config.main import Config
from tox.config.sets import ConfigSet, EnvConfigSet
from tox.config.source.api import Section

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from tests.conftest import ToxIniCreator
    from tox.pytest import ToxProjectCreator

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
        keys="optional_none",
        of_type=Optional[int],  # type: ignore[arg-type]
        default=None,
        desc="optional_none",
    )
    optional_none = config_set["optional_none"]
    assert optional_none is None


def test_config_dict(conf_builder: ConfBuilder) -> None:
    config_set = conf_builder("dict = a=1\n  b=2\n  c=3")
    config_set.add_config(keys="dict", of_type=Dict[str, int], default={}, desc="dict")
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
    assert str(context.value) == "dictionary lines must be of form key=value, found 'something'"


def test_config_bad_bool(conf_builder: ConfBuilder) -> None:
    config_set = conf_builder("bad_bool = whatever")
    config_set.add_config(keys="bad_bool", of_type=bool, default=False, desc="bad_bool")
    with pytest.raises(TypeError) as context:
        assert config_set["bad_bool"]
    error = "value 'whatever' cannot be transformed to bool, valid: , 0, 1, false, no, off, on, true, yes"
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
    msg = (
        "duplicate configuration definition for py39:\n"
        "has: ConfigConstantDefinition(keys=('path',), desc=desc, value=value)\n"
        "new: ConfigConstantDefinition(keys=('path',), desc=desc2, value=value)"
    )
    with pytest.raises(ValueError, match=re.escape(msg)):
        config_set.add_constant(keys="path", desc="desc2", value="value")


def test_config_redefine_dynamic_fail(conf_builder: ConfBuilder) -> None:
    config_set = conf_builder("path = path")
    config_set.add_config(keys="path", of_type=str, default="default_1", desc="path")
    msg = (
        "duplicate configuration definition for py39:\n"
        "has: ConfigDynamicDefinition(keys=('path',), desc=path, of_type=<class 'str'>, default=default_1)\n"
        "new: ConfigDynamicDefinition(keys=('path',), desc=path, of_type=<class 'str'>, default=default_2)"
    )
    with pytest.raises(ValueError, match=re.escape(msg)):
        config_set.add_config(keys="path", of_type=str, default="default_2", desc="path")


def test_config_dynamic_not_equal(conf_builder: ConfBuilder) -> None:
    config_set = conf_builder("")
    path = config_set.add_config(keys="path", of_type=Path, default=Path(), desc="path")
    paths = config_set.add_config(keys="paths", of_type=Path, default=Path(), desc="path")
    assert path != paths


def test_define_custom_set(tox_project: ToxProjectCreator) -> None:
    class MagicConfigSet(ConfigSet):
        SECTION = Section(None, "magic")

        def register_config(self) -> None:
            self.add_config("a", of_type=int, default=0, desc="number")
            self.add_config("b", of_type=str, default="", desc="string")

    project = tox_project({"tox.ini": "[testenv]\npackage=skip\n[A]\na=1\n[magic]\nb = ok"})
    result = project.run()
    section = MagicConfigSet.SECTION
    conf = result.state.conf.get_section_config(section, base=["A"], of_type=MagicConfigSet, for_env=None)
    assert conf["a"] == 1
    assert conf["b"] == "ok"
    exp = "MagicConfigSet(loaders=[IniLoader(section=magic, overrides={}), IniLoader(section=A, overrides={})])"
    assert repr(conf) == exp

    assert isinstance(result.state.conf._options, Parsed)  # noqa: SLF001


def test_do_not_allow_create_config_set(mocker: MockerFixture) -> None:
    with pytest.raises(TypeError, match="Can't instantiate"):
        ConfigSet(mocker.create_autospec(Config))  # type: ignore[abstract,call-arg]


def test_set_env_raises_on_non_str(mocker: MockerFixture) -> None:
    env_set = EnvConfigSet(mocker.create_autospec(Config), Section("a", "b"), "b")
    env_set.loaders.insert(0, MemoryLoader(set_env=1))
    with pytest.raises(TypeError, match="1"):
        assert env_set["set_env"]


@pytest.mark.parametrize("work_dir", ["a", ""])
def test_config_work_dir(tox_project: ToxProjectCreator, work_dir: str) -> None:
    project = tox_project({"tox.ini": "[tox]\ntoxworkdir=b"})
    result = project.run("c", *(["--workdir", str(project.path / work_dir)] if work_dir else []))
    expected = project.path / work_dir if work_dir else Path("b")
    assert expected == result.state.conf.core["work_dir"]
