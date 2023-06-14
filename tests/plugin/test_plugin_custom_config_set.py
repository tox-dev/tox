from __future__ import annotations

import logging
from functools import partial
from typing import TYPE_CHECKING, Optional

import pytest

from tox.config.loader.section import Section
from tox.config.sets import ConfigSet, EnvConfigSet
from tox.plugin import impl
from tox.pytest import ToxProjectCreator, register_inline_plugin

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from tox.session.state import State
    from tox.tox_env.api import ToxEnv


@pytest.fixture(autouse=True)
def _custom_config_set(mocker: MockerFixture) -> None:
    class DockerConfigSet(ConfigSet):
        def register_config(self) -> None:
            self.add_config(keys="A", of_type=int, default=0, desc="a config")

    @impl
    def tox_add_env_config(env_conf: EnvConfigSet, state: State) -> None:
        def factory(for_env: str, raw: object) -> DockerConfigSet:
            assert isinstance(raw, str)
            section = Section("docker", raw)
            return state.conf.get_section_config(section, base=["docker"], of_type=DockerConfigSet, for_env=for_env)

        env_conf.add_config(
            "docker",
            of_type=Optional[DockerConfigSet],  # type: ignore[arg-type] # mypy fails to understand the type info
            default=None,
            desc="docker env",
            factory=partial(factory, env_conf.name),
        )

    @impl
    def tox_before_run_commands(tox_env: ToxEnv) -> None:
        docker: DockerConfigSet | None = tox_env.conf["docker"]
        assert docker is not None
        logging.warning("Name=%s env=%s A=%d", docker.name, docker.env_name, docker["A"])

    register_inline_plugin(mocker, tox_add_env_config, tox_before_run_commands)


def test_define_custom_config_set(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[testenv]\npackage=skip\ndocker=a\n[docker:a]\nA=2"})
    result = project.run()
    result.assert_success()
    assert "py: Name=a env=py A=2" in result.out


def test_define_custom_config_base(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[testenv]\npackage=skip\ndocker=a\n[docker]\nA=2"})
    result = project.run()
    result.assert_success()
    assert "py: Name=a env=py A=2" in result.out


def test_define_custom_config_override_base(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[testenv]\npackage=skip\ndocker=a\n[M]\nA=2\n[docker:a]\nbase=M"})
    result = project.run()
    result.assert_success()
    assert "py: Name=a env=py A=2" in result.out


def test_define_custom_config_override_base_implicit(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[testenv]\npackage=skip\ndocker=a\n[docker:M]\nA=2\n[docker:a]\nbase=M"})
    result = project.run()
    result.assert_success()
    assert "py: Name=a env=py A=2" in result.out


def test_define_custom_config_replace(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[testenv]\npackage=skip\ndocker=a\n[docker]\nA={[docker]B}\nB=2"})
    result = project.run()
    result.assert_success()
    assert "py: Name=a env=py A=2" in result.out


def test_define_custom_config_factor_filter(tox_project: ToxProjectCreator) -> None:
    ini = """
    [tox]
    env_list =
        a
        b
    [testenv]
    package = skip
    docker = db
    [docker:db]
    A =
        a: 1
        b: 2"""
    project = tox_project({"tox.ini": ini})
    result = project.run("r", "-e", "a,b")
    result.assert_success()
    assert "a: Name=db env=a A=1" in result.out
    assert "b: Name=db env=b A=2" in result.out
