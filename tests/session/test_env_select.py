from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tox.config.cli.parse import get_options
from tox.session.env_select import CliEnv, EnvSelector
from tox.session.state import State

if TYPE_CHECKING:
    from tox.pytest import MonkeyPatch, ToxProjectCreator


def test_label_core_can_define(tox_project: ToxProjectCreator) -> None:
    ini = """
        [tox]
        labels =
            test = py3{10,9}
            static = flake8, type
        """
    project = tox_project({"tox.ini": ini})
    outcome = project.run("l", "--no-desc")
    outcome.assert_success()
    outcome.assert_out_err("py\npy310\npy39\nflake8\ntype\n", "")


def test_label_core_select(tox_project: ToxProjectCreator) -> None:
    ini = """
        [tox]
        labels =
            test = py3{10,9}
            static = flake8, type
        """
    project = tox_project({"tox.ini": ini})
    outcome = project.run("l", "--no-desc", "-m", "test")
    outcome.assert_success()
    outcome.assert_out_err("py310\npy39\n", "")


def test_label_select_trait(tox_project: ToxProjectCreator) -> None:
    ini = """
        [tox]
        env_list = py310, py39, flake8, type
        [testenv]
        labels = test
        [testenv:flake8]
        labels = static
        [testenv:type]
        labels = static
        """
    project = tox_project({"tox.ini": ini})
    outcome = project.run("l", "--no-desc", "-m", "test")
    outcome.assert_success()
    outcome.assert_out_err("py310\npy39\n", "")


def test_label_core_and_trait(tox_project: ToxProjectCreator) -> None:
    ini = """
        [tox]
        env_list = py310, py39, flake8, type
        labels =
            static = flake8, type
        [testenv]
        labels = test
        """
    project = tox_project({"tox.ini": ini})
    outcome = project.run("l", "--no-desc", "-m", "test", "static")
    outcome.assert_success()
    outcome.assert_out_err("py310\npy39\nflake8\ntype\n", "")


@pytest.mark.parametrize(
    ("selection_arguments", "expect_envs"),
    [
        (
            ("-f", "cov", "django20"),
            ("py310-django20-cov", "py39-django20-cov"),
        ),
        (
            ("-f", "cov-django20"),
            ("py310-django20-cov", "py39-django20-cov"),
        ),
        (
            ("-f", "py39", "django20", "-f", "py310", "django21"),
            ("py310-django21-cov", "py310-django21", "py39-django20-cov", "py39-django20"),
        ),
    ],
)
def test_factor_select(
    tox_project: ToxProjectCreator,
    selection_arguments: tuple[str, ...],
    expect_envs: tuple[str, ...],
) -> None:
    ini = """
        [tox]
        env_list = py3{10,9}-{django20,django21}{-cov,}
        """
    project = tox_project({"tox.ini": ini})
    outcome = project.run("l", "--no-desc", *selection_arguments)
    outcome.assert_success()
    outcome.assert_out_err("{}\n".format("\n".join(expect_envs)), "")


def test_tox_skip_env(tox_project: ToxProjectCreator, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("TOX_SKIP_ENV", "m[y]py")
    project = tox_project({"tox.ini": "[tox]\nenv_list = py3{10,9},mypy"})
    outcome = project.run("l", "--no-desc", "-q")
    outcome.assert_success()
    outcome.assert_out_err("py310\npy39\n", "")


def test_tox_skip_env_cli(tox_project: ToxProjectCreator, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("TOX_SKIP_ENV", raising=False)
    project = tox_project({"tox.ini": "[tox]\nenv_list = py3{10,9},mypy"})
    outcome = project.run("l", "--no-desc", "-q", "--skip-env", "m[y]py")
    outcome.assert_success()
    outcome.assert_out_err("py310\npy39\n", "")


def test_tox_skip_env_logs(tox_project: ToxProjectCreator, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("TOX_SKIP_ENV", "m[y]py")
    project = tox_project({"tox.ini": "[tox]\nenv_list = py3{10,9},mypy"})
    outcome = project.run("l", "--no-desc")
    outcome.assert_success()
    outcome.assert_out_err("ROOT: skip environment mypy, matches filter 'm[y]py'\npy310\npy39\n", "")


def test_env_select_lazily_looks_at_envs() -> None:
    state = State(get_options(), [])
    env_selector = EnvSelector(state)
    # late-assigning env should be reflected in env_selector
    state.conf.options.env = CliEnv("py")
    assert set(env_selector.iter()) == {"py"}


def test_cli_env_can_be_specified_in_default(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": "[tox]\nenv_list=exists"})
    outcome = proj.run("r", "-e", "exists")
    outcome.assert_success()
    assert "exists" in outcome.out
    assert not outcome.err


def test_cli_env_can_be_specified_in_additional_environments(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": "[testenv:exists]"})
    outcome = proj.run("r", "-e", "exists")
    outcome.assert_success()
    assert "exists" in outcome.out
    assert not outcome.err


def test_cli_env_not_in_tox_config_fails(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": ""})
    outcome = proj.run("r", "-e", "does_not_exist")
    outcome.assert_failed(code=-2)
    assert "provided environments not found in configuration file: ['does_not_exist']" in outcome.out, outcome.out


@pytest.mark.parametrize("env_name", ["py", "py310", ".pkg"])
def test_allowed_implicit_cli_envs(env_name: str, tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": ""})
    outcome = proj.run("r", "-e", env_name)
    outcome.assert_success()
    assert env_name in outcome.out
    assert not outcome.err
