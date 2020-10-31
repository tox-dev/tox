from typing import Callable

import pytest

from tox.config.sets import ConfigSet
from tox.pytest import ToxProjectCreator

EnvConfigCreator = Callable[[str], ConfigSet]


@pytest.fixture()
def example(tox_project: ToxProjectCreator) -> EnvConfigCreator:
    def func(conf: str) -> ConfigSet:
        project = tox_project({"tox.ini": f"""[tox]\nenv_list = a\n[testenv]\n{conf}\n"""})
        config = project.config()
        env_config = config.get_env("a")
        return env_config

    return func


def test_replace_within_tox_env(example: EnvConfigCreator) -> None:
    env_config = example("r = 1\no = {r}")
    env_config.add_config(keys="r", of_type=str, default="r", desc="r")
    env_config.add_config(keys="o", of_type=str, default="o", desc="o")
    result = env_config["o"]
    assert result == "1"


def test_replace_within_tox_env_missing_no_default_leaves(example: EnvConfigCreator) -> None:
    env_config = example("o = {p}")
    env_config.add_config(keys="o", of_type=str, default="o", desc="o")
    result = env_config["o"]
    assert result == "{p}"


def test_replace_within_tox_env_missing_default(example: EnvConfigCreator) -> None:
    env_config = example("o = {p:one}")
    env_config.add_config(keys="o", of_type=str, default="o", desc="o")
    result = env_config["o"]
    assert result == "one"


def test_replace_within_tox_env_missing_default_env_only(example: EnvConfigCreator) -> None:
    env_config = example("o = {[testenv:a]p:one}")
    env_config.add_config(keys="o", of_type=str, default="o", desc="o")
    result = env_config["o"]
    assert result == "one"


def test_replace_within_tox_env_from_base(example: EnvConfigCreator) -> None:
    env_config = example("p = one\n[testenv:a]\no = {[testenv]p}")
    env_config.add_config(keys="p", of_type=str, default="p", desc="p")
    env_config.add_config(keys="o", of_type=str, default="o", desc="o")
    result = env_config["o"]
    assert result == "one"
