from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from tox.pytest import ToxProjectCreator


def test_legacy_show_config(tox_project: ToxProjectCreator, mocker: MockerFixture) -> None:
    show_config = mocker.patch("tox.session.cmd.legacy.show_config")

    outcome = tox_project({"tox.ini": ""}).run("le", "--showconfig")

    assert show_config.call_count == 1
    assert outcome.state.options.list_keys_only == []
    assert outcome.state.options.show_core is True


@pytest.mark.parametrize("verbose", range(3))
def test_legacy_list_default(tox_project: ToxProjectCreator, mocker: MockerFixture, verbose: int) -> None:
    list_env = mocker.patch("tox.session.cmd.legacy.list_env")

    outcome = tox_project({"tox.ini": ""}).run("le", "-l", *(["-v"] * verbose))

    assert list_env.call_count == 1
    assert outcome.state.options.list_no_description is (verbose < 1)
    assert outcome.state.options.list_default_only is True
    assert outcome.state.options.show_core is False


@pytest.mark.parametrize("verbose", range(3))
def test_legacy_list_all(tox_project: ToxProjectCreator, mocker: MockerFixture, verbose: int) -> None:
    list_env = mocker.patch("tox.session.cmd.legacy.list_env")

    outcome = tox_project({"tox.ini": ""}).run("le", "-a", *(["-v"] * verbose))

    assert list_env.call_count == 1
    assert outcome.state.options.list_no_description is (verbose < 1)
    assert outcome.state.options.list_default_only is False
    assert outcome.state.options.show_core is False


def test_legacy_devenv(tox_project: ToxProjectCreator, mocker: MockerFixture, tmp_path: Path) -> None:
    devenv = mocker.patch("tox.session.cmd.legacy.devenv")
    into = tmp_path / "b"

    outcome = tox_project({"tox.ini": ""}).run("le", "--devenv", str(into), "-e", "py")

    assert devenv.call_count == 1
    assert outcome.state.options.devenv_path == into


def test_legacy_run_parallel(tox_project: ToxProjectCreator, mocker: MockerFixture) -> None:
    run_parallel = mocker.patch("tox.session.cmd.legacy.run_parallel")

    tox_project({"tox.ini": ""}).run("le", "-p", "all", "-e", "py")

    assert run_parallel.call_count == 1


def test_legacy_run_sequential(tox_project: ToxProjectCreator, mocker: MockerFixture) -> None:
    run_sequential = mocker.patch("tox.session.cmd.legacy.run_sequential")

    tox_project({"tox.ini": ""}).run("le", "-e", "py")

    assert run_sequential.call_count == 1
