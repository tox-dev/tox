from __future__ import annotations

import logging
import os
import sys
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest

from tox.config.cli.parser import ToxParser
from tox.config.loader.memory import MemoryLoader
from tox.config.sets import ConfigSet, CoreConfigSet, EnvConfigSet
from tox.execute import Outcome
from tox.plugin import impl
from tox.pytest import ToxProjectCreator, register_inline_plugin
from tox.session.state import State
from tox.tox_env.api import ToxEnv
from tox.tox_env.register import ToxEnvRegister

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


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
    def tox_add_core_config(core_conf: CoreConfigSet, state: State) -> None:
        assert isinstance(core_conf, CoreConfigSet)
        assert isinstance(state, State)
        logging.warning("tox_add_core_config")

    @impl
    def tox_add_env_config(env_conf: EnvConfigSet, state: State) -> None:
        assert isinstance(env_conf, EnvConfigSet)
        assert isinstance(state, State)
        logging.warning("tox_add_env_config")

    @impl
    def tox_before_run_commands(tox_env: ToxEnv) -> None:
        assert isinstance(tox_env, ToxEnv)
        logging.warning("tox_before_run_commands")

    @impl
    def tox_on_install(tox_env: ToxEnv, arguments: Any, section: str, of_type: str) -> None:
        assert isinstance(tox_env, ToxEnv)
        assert arguments is not None
        assert isinstance(section, str)
        assert isinstance(of_type, str)
        logging.warning("tox_on_install %s %s", section, of_type)

    @impl
    def tox_after_run_commands(tox_env: ToxEnv, exit_code: int, outcomes: list[Outcome]) -> None:
        assert isinstance(tox_env, ToxEnv)
        assert exit_code == 0
        assert isinstance(outcomes, list)
        assert all(isinstance(i, Outcome) for i in outcomes)
        logging.warning("tox_after_run_commands")

    @impl
    def tox_env_teardown(tox_env: ToxEnv) -> None:
        assert isinstance(tox_env, ToxEnv)
        logging.warning("teardown")

    plugins = tuple(v for v in locals().values() if callable(v) and hasattr(v, "tox_impl"))
    assert len(plugins) == 8
    register_inline_plugin(mocker, *plugins)

    tox_ini = """
        [tox]
        env_list=a,b
        [testenv]
        package=skip
        commands=python -c 'print(1)'
        env_list=a,b
    """
    project = tox_project({"tox.ini": tox_ini})
    result = project.run("r", "-e", "a,b")
    result.assert_success()
    cmd = "print(1)" if sys.platform == "win32" else "'print(1)'"
    expected = [
        "ROOT: tox_register_tox_env",
        "ROOT: tox_add_option",
        "ROOT: tox_add_core_config",
        "a: tox_add_env_config",
        "b: tox_add_env_config",
        "a: tox_on_install PythonRun deps",
        "a: tox_before_run_commands",
        f"a: commands[0]> python -c {cmd}",
        mocker.ANY,  # output a
        "a: tox_after_run_commands",
        "a: teardown",
        mocker.ANY,  # report finished A
        "b: tox_on_install PythonRun deps",
        "b: tox_before_run_commands",
        f"b: commands[0]> python -c {cmd}",
        mocker.ANY,  # output b
        "b: tox_after_run_commands",
        "b: teardown",
        mocker.ANY,  # report a
        mocker.ANY,  # report b
        mocker.ANY,  # overall report
    ]
    assert result.out.splitlines() == expected, result.out


@pytest.mark.parametrize(
    "dir_name",
    [
        "tox_root",
        "work_dir",
        "temp_dir",
    ],
)
def test_plugin_can_set_core_conf(
    tox_project: ToxProjectCreator,
    mocker: MockerFixture,
    dir_name: str,
    tmp_path: Path,
) -> None:
    @impl
    def tox_add_core_config(core_conf: CoreConfigSet, state: State) -> None:  # noqa: ARG001
        core_conf.loaders.insert(0, MemoryLoader(**{dir_name: tmp_path}))

    register_inline_plugin(mocker, tox_add_core_config)

    project = tox_project({})
    result = project.run("c")
    result.assert_success()

    assert result.state.conf.core[dir_name] == tmp_path


def test_plugin_can_read_env_list(tox_project: ToxProjectCreator, mocker: MockerFixture) -> None:
    @impl
    def tox_add_core_config(core_conf: CoreConfigSet, state: State) -> None:  # noqa: ARG001
        logging.warning("All envs: %s", ", ".join(state.envs.iter(only_active=False)))
        logging.warning("Default envs: %s", ", ".join(state.envs.iter(only_active=True)))

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
    assert "ROOT: All envs: explicit, section, implicit" in result.out
    assert "ROOT: Default envs: explicit" in result.out


def test_plugin_can_read_sections(tox_project: ToxProjectCreator, mocker: MockerFixture) -> None:
    @impl
    def tox_add_core_config(core_conf: CoreConfigSet, state: State) -> None:  # noqa: ARG001
        logging.warning("Sections: %s", ", ".join(i.key for i in state.conf.sections()))

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
    def tox_add_env_config(env_conf: EnvConfigSet, state: State) -> None:  # noqa: ARG001
        env_conf.loaders.insert(0, MemoryLoader(deps=[1]))
        with pytest.raises(TypeError, match="1"):
            assert env_conf["deps"]

    register_inline_plugin(mocker, tox_add_env_config)
    project = tox_project({"tox.ini": "[testenv]\npackage=skip"})
    result = project.run()
    result.assert_failed()
    assert "raise TypeError(raw)" in result.out


def test_plugin_extend_pass_env(tox_project: ToxProjectCreator, mocker: MockerFixture) -> None:
    @impl
    def tox_add_env_config(env_conf: EnvConfigSet, state: State) -> None:  # noqa: ARG001
        env_conf["pass_env"].append("MAGIC_*")

    register_inline_plugin(mocker, tox_add_env_config)
    ini = """
    [testenv]
    package=skip
    commands=python -c 'import os; print(os.environ["MAGIC_1"]); print(os.environ["MAGIC_2"])'
    """
    project = tox_project({"tox.ini": ini})
    with patch.dict(os.environ, {"MAGIC_1": "magic_1", "MAGIC_2": "magic_2"}):
        result = project.run("r")
    result.assert_success()
    assert "magic_1" in result.out
    assert "magic_2" in result.out

    result_conf = project.run("c", "-e", "py", "-k", "pass_env")
    result_conf.assert_success()
    assert "MAGIC_*" in result_conf.out


def test_plugin_extend_set_env(tox_project: ToxProjectCreator, mocker: MockerFixture) -> None:
    @impl
    def tox_add_env_config(env_conf: EnvConfigSet, state: State) -> None:  # noqa: ARG001
        env_conf["set_env"].update({"MAGI_CAL": "magi_cal"})

    register_inline_plugin(mocker, tox_add_env_config)
    ini = """
    [testenv]
    package=skip
    commands=python -c 'import os; print(os.environ["MAGI_CAL"])'
    """
    project = tox_project({"tox.ini": ini})
    result = project.run("r")
    result.assert_success()
    assert "magi_cal" in result.out

    result_conf = project.run("c", "-e", "py", "-k", "set_env")
    result_conf.assert_success()
    assert "MAGI_CAL=magi_cal" in result_conf.out


def test_plugin_config_frozen_past_add_env(tox_project: ToxProjectCreator, mocker: MockerFixture) -> None:
    def _cannot_extend_config(config_set: ConfigSet) -> None:
        for _conf in (
            lambda c: c.add_constant("c", "desc", "v"),
            lambda c: c.add_config("c", of_type=str, default="c", desc="d"),
        ):
            try:
                _conf(config_set)  # type: ignore[no-untyped-call] # call to not typed function
                raise NotImplementedError
            except RuntimeError as exc:  # noqa: PERF203
                assert str(exc) == "config set has been marked final and cannot be extended"  # noqa: PT017

    @impl
    def tox_before_run_commands(tox_env: ToxEnv) -> None:
        _cannot_extend_config(tox_env.conf)
        _cannot_extend_config(tox_env.core)

    @impl
    def tox_after_run_commands(tox_env: ToxEnv, exit_code: int, outcomes: list[Outcome]) -> None:  # noqa: ARG001
        _cannot_extend_config(tox_env.conf)
        _cannot_extend_config(tox_env.core)

    register_inline_plugin(mocker, tox_before_run_commands, tox_after_run_commands)

    project = tox_project({"tox.ini": "[testenv]\npackage=skip"})
    result = project.run("r")
    result.assert_success()
