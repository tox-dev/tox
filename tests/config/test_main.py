import pytest

from tests.conftest import ToxIniCreator
from tox.config.loader.api import Override
from tox.config.loader.memory import MemoryLoader
from tox.config.main import Config
from tox.config.sets import ConfigSet


@pytest.fixture
def empty_config(tox_ini_conf: ToxIniCreator) -> Config:
    return tox_ini_conf("")


def test_empty_config_repr(empty_config: Config) -> None:
    text = repr(empty_config)
    assert str(empty_config.core["tox_root"]) in text
    assert "config_source=ToxIni" in text


def test_empty_conf_tox_envs(empty_config: Config) -> None:
    tox_env_keys = list(empty_config)
    assert tox_env_keys == []


def test_empty_conf_get(empty_config: Config) -> None:
    result = empty_config.get_env("magic")
    assert isinstance(result, ConfigSet)
    loaders = result["base"]
    assert loaders == ["testenv"]


def test_config_some_envs(tox_ini_conf: ToxIniCreator) -> None:
    example = """
    [tox]
    env_list = py38, py37
    [testenv]
    deps = 1
        other: 2
    [testenv:magic]
    """
    config = tox_ini_conf(example)
    tox_env_keys = list(config)
    assert tox_env_keys == ["py38", "py37", "other", "magic"]

    config_set = config.get_env("py38")
    assert repr(config_set)
    assert isinstance(config_set, ConfigSet)
    assert list(config_set)


def test_config_overrides(tox_ini_conf: ToxIniCreator) -> None:
    conf = tox_ini_conf("[testenv]", override=[Override("testenv.c=ok")]).get_env("py")
    conf.add_config("c", of_type=str, default="d", desc="desc")
    assert conf["c"] == "ok"


def test_config_new_source(tox_ini_conf: ToxIniCreator) -> None:
    main_conf = tox_ini_conf("[testenv]", override=[Override("testenv.c=ok")])
    conf = main_conf.get_env("py", loaders=[MemoryLoader(c="something_else")])
    conf.add_config("c", of_type=str, default="d", desc="desc")
    assert conf["c"] == "something_else"
