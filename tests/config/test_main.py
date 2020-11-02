import pytest

from tox.config.loader.api import Override
from tox.config.loader.memory import MemoryLoader
from tox.config.main import Config
from tox.config.sets import ConfigSet
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
    result = empty_config.get_env("magic")
    assert isinstance(result, ConfigSet)
    loaders = result["base"]
    assert loaders == ["testenv"]


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

    config_set = config.get_env("py38")
    assert repr(config_set)
    assert isinstance(config_set, ConfigSet)
    assert list(config_set) == ["base"]


def test_config_overrides(tox_project: ToxProjectCreator) -> None:
    conf = tox_project({"tox.ini": "[testenv]"}).config(override=[Override("testenv.c=ok")]).get_env("py")
    conf.add_config("c", of_type=str, default="d", desc="desc")
    assert conf["c"] == "ok"


def test_config_new_source(tox_project: ToxProjectCreator) -> None:
    main_conf = tox_project({"tox.ini": "[testenv]"}).config(override=[Override("testenv.c=ok")])
    conf = main_conf.get_env("py", loaders=[MemoryLoader(c="something_else")])
    conf.add_config("c", of_type=str, default="d", desc="desc")
    assert conf["c"] == "something_else"
