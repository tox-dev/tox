import logging
import sys
from typing import List

import pytest
from pytest_mock import MockerFixture

from tox.config.cli.parser import ToxParser
from tox.config.loader.memory import MemoryLoader
from tox.config.main import Config
from tox.config.sets import CoreConfigSet, EnvConfigSet
from tox.execute import Outcome
from tox.plugin import impl
from tox.pytest import ToxProjectCreator, register_inline_plugin
from tox.tox_env.api import ToxEnv
from tox.tox_env.register import ToxEnvRegister


def test_plugin_hooks_and_order(tox_project: ToxProjectCreator, mocker: MockerFixture) -> None:
    @impl
    def tox_register_tox_env(register: ToxEnvRegister) -> None:
        assert isinstance(register, ToxEnvRegister)
        logging.warning("tox_register_tox_env")

    @impl
    def tox_add_option(parser: ToxParser) -> None:
        assert isinstance(parser, ToxParser)
        logging.warning("tox_add_option")

    @impl
    def tox_add_core_config(core_conf: CoreConfigSet, config: Config) -> None:
        assert isinstance(core_conf, CoreConfigSet)
        assert isinstance(config, Config)
        logging.warning("tox_add_core_config")

    @impl
    def tox_add_env_config(env_conf: EnvConfigSet, config: Config) -> None:
        assert isinstance(env_conf, EnvConfigSet)
        assert isinstance(config, Config)
        logging.warning("tox_add_env_config")

    @impl
    def tox_before_run_commands(tox_env: ToxEnv) -> None:
        assert isinstance(tox_env, ToxEnv)
        logging.warning("tox_before_run_commands")

    @impl
    def tox_after_run_commands(tox_env: ToxEnv, exit_code: int, outcomes: List[Outcome]) -> None:
        assert isinstance(tox_env, ToxEnv)
        assert exit_code == 0
        assert isinstance(outcomes, list)
        assert all(isinstance(i, Outcome) for i in outcomes)
        logging.warning("tox_after_run_commands")

    plugins = tuple(v for v in locals().values() if callable(v) and hasattr(v, "tox_impl"))
    assert len(plugins) == 6
    register_inline_plugin(mocker, *plugins)
    project = tox_project({"tox.ini": "[testenv]\npackage=skip\ncommands=python -c 'print(1)'"})
    result = project.run("r", "-e", "a,b")
    result.assert_success()
    cmd = "print(1)" if sys.platform == "win32" else "'print(1)'"
    expected = [
        "ROOT: tox_register_tox_env",
        "ROOT: tox_add_option",
        "ROOT: tox_add_core_config",
        "a: tox_add_env_config",
        "b: tox_add_env_config",
        "a: tox_before_run_commands",
        f"a: commands[0]> python -c {cmd}",
        mocker.ANY,  # output a
        "a: tox_after_run_commands",
        mocker.ANY,  # report finished A
        "b: tox_before_run_commands",
        f"b: commands[0]> python -c {cmd}",
        mocker.ANY,  # output b
        "b: tox_after_run_commands",
        mocker.ANY,  # report a
        mocker.ANY,  # report b
        mocker.ANY,  # overall report
    ]
    assert result.out.splitlines() == expected, result.out


def test_plugin_can_read_env_list(tox_project: ToxProjectCreator, mocker: MockerFixture) -> None:
    @impl
    def tox_add_core_config(core_conf: CoreConfigSet, config: Config) -> None:
        logging.warning("All envs: %s", ", ".join(config.env_list(everything=True)))
        logging.warning("Default envs: %s", ", ".join(config.env_list()))

    register_inline_plugin(mocker, tox_add_core_config)
    ini = """
    [tox]
    env_list = explicit
    [testenv]
    package = skip
    set_env =
        implicit: A=1
    [testenv:section]
    """
    project = tox_project({"tox.ini": ini})
    result = project.run()
    assert "ROOT: All envs: explicit, implicit, section" in result.out
    assert "ROOT: Default envs: explicit" in result.out


def test_plugin_can_read_sections(tox_project: ToxProjectCreator, mocker: MockerFixture) -> None:
    @impl
    def tox_add_core_config(core_conf: CoreConfigSet, config: Config) -> None:
        logging.warning("Sections: %s", ", ".join(i.key for i in config.sections()))

    register_inline_plugin(mocker, tox_add_core_config)
    ini = """
    [tox]
    [testenv]
    package = skip
    [testenv:section]
    [other:section]
    """
    project = tox_project({"tox.ini": ini})
    result = project.run()
    result.assert_success()
    assert "ROOT: Sections: tox, testenv, testenv:section, other:section" in result.out


def test_plugin_injects_invalid_python_run(tox_project: ToxProjectCreator, mocker: MockerFixture) -> None:
    @impl
    def tox_add_env_config(env_conf: EnvConfigSet, config: Config) -> None:
        env_conf.loaders.insert(0, MemoryLoader(deps=[1]))
        with pytest.raises(TypeError, match="1"):
            assert env_conf["deps"]

    register_inline_plugin(mocker, tox_add_env_config)
    project = tox_project({"tox.ini": "[testenv]\npackage=skip"})
    result = project.run()
    result.assert_failed()
    assert "raise TypeError(raw)" in result.out
