from textwrap import dedent

import pytest

from tox.pytest import ToxProjectCreator


@pytest.fixture()
def example(tox_project: ToxProjectCreator):
    def func(conf):
        project = tox_project(
            {
                "tox.ini": dedent(
                    """
                        [tox]
                        env_list = a
                        [testenv]
                        {}
                        """
                ).format(conf)
            }
        )
        config = project.config()
        env_config = config["a"]
        return env_config

    return func


def test_replace_within_tox_env(example):
    env_config = example("r = 1\no = {r}")
    env_config.add_config(keys="r", of_type=str, default="r", desc="r")
    env_config.add_config(keys="o", of_type=str, default="o", desc="o")
    result = env_config["o"]
    assert result == "1"


def test_replace_within_tox_env_missing_no_default_leaves(example):
    env_config = example("o = {p}")
    env_config.add_config(keys="o", of_type=str, default="o", desc="o")
    result = env_config["o"]
    assert result == "{p}"


def test_replace_within_tox_env_missing_default(example):
    env_config = example("o = {p:one}")
    env_config.add_config(keys="o", of_type=str, default="o", desc="o")
    result = env_config["o"]
    assert result == "one"


def test_replace_within_tox_env_missing_default_env_only(example):
    env_config = example("o = {[testenv:a]p:one}")
    env_config.add_config(keys="o", of_type=str, default="o", desc="o")
    result = env_config["o"]
    assert result == "one"


def test_replace_within_tox_env_from_base(example):
    env_config = example("p = one\n[testenv:a]\no = {[testenv]p}")
    env_config.add_config(keys="p", of_type=str, default="p", desc="p")
    env_config.add_config(keys="o", of_type=str, default="o", desc="o")
    result = env_config["o"]
    assert result == "one"
