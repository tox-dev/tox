from __future__ import annotations

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from tox.pytest import ToxProjectCreator


def test_legacy_show_config(tox_project: ToxProjectCreator, mocker: MockerFixture) -> None:
    show_config = mocker.patch("tox.session.cmd.legacy.show_config")

    outcome = tox_project({"tox.ini": ""}).run("le", "--showconfig")

    assert show_config.call_count == 1
    assert outcome.state.conf.options.list_keys_only == []
    assert outcome.state.conf.options.show_core is True


@pytest.mark.parametrize("verbose", range(3))
def test_legacy_list_default(tox_project: ToxProjectCreator, mocker: MockerFixture, verbose: int) -> None:
    list_env = mocker.patch("tox.session.cmd.legacy.list_env")

    outcome = tox_project({"tox.ini": ""}).run("le", "-l", *(["-v"] * verbose))

    assert list_env.call_count == 1
    assert outcome.state.conf.options.list_no_description is (verbose < 1)
    assert outcome.state.conf.options.list_default_only is True
    assert outcome.state.conf.options.show_core is False


@pytest.mark.parametrize(
    "configuration",
    [
        pytest.param("", id="missing toxenv section"),
        pytest.param("[toxenv]", id="missing envlist"),
        pytest.param("[toxenv]\nenv_list=", id="empty envlist"),
    ],
)
def test_legacy_list_env_with_empty_or_missing_env_list(tox_project: ToxProjectCreator, configuration: str) -> None:
    """we want to stay backwards compatible with tox 3 and show no output"""
    outcome = tox_project({"tox.ini": configuration}).run("le", "-l")

    outcome.assert_success()
    outcome.assert_out_err("", "")


def test_legacy_list_env_with_no_tox_file(tox_project: ToxProjectCreator) -> None:
    project = tox_project({})
    outcome = project.run("le", "-l")

    outcome.assert_success()
    out = f"ROOT: No tox.ini or setup.cfg or pyproject.toml found, assuming empty tox.ini at {project.path}\n"
    outcome.assert_out_err(out, "")


@pytest.mark.parametrize("verbose", range(3))
def test_legacy_list_all(tox_project: ToxProjectCreator, mocker: MockerFixture, verbose: int) -> None:
    list_env = mocker.patch("tox.session.cmd.legacy.list_env")

    outcome = tox_project({"tox.ini": ""}).run("le", "-a", *(["-v"] * verbose))

    assert list_env.call_count == 1
    assert outcome.state.conf.options.list_no_description is (verbose < 1)
    assert outcome.state.conf.options.list_default_only is False
    assert outcome.state.conf.options.show_core is False


def test_legacy_devenv(tox_project: ToxProjectCreator, mocker: MockerFixture, tmp_path: Path) -> None:
    devenv = mocker.patch("tox.session.cmd.legacy.devenv")
    into = tmp_path / "b"

    outcome = tox_project({"tox.ini": ""}).run("le", "--devenv", str(into), "-e", "py")

    assert devenv.call_count == 1
    assert outcome.state.conf.options.devenv_path == into


def test_legacy_run_parallel(tox_project: ToxProjectCreator, mocker: MockerFixture) -> None:
    run_parallel = mocker.patch("tox.session.cmd.legacy.run_parallel")

    tox_project({"tox.ini": ""}).run("le", "-p", "all", "-e", "py")

    assert run_parallel.call_count == 1


def test_legacy_run_sequential(tox_project: ToxProjectCreator, mocker: MockerFixture) -> None:
    run_sequential = mocker.patch("tox.session.cmd.legacy.run_sequential")

    tox_project({"tox.ini": ""}).run("le", "-e", "py")

    assert run_sequential.call_count == 1


def test_legacy_help(tox_project: ToxProjectCreator) -> None:
    outcome = tox_project({"tox.ini": ""}).run("le", "-h")
    outcome.assert_success()
