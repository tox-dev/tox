from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

    from tox.pytest import ToxProjectCreator


def test_legacy_show_config(tox_project: ToxProjectCreator, mocker: MockerFixture) -> None:
    show_config = mocker.patch("tox.session.cmd.legacy.show_config")

    outcome = tox_project({"tox.ini": ""}).run("le", "--showconfig")

    assert show_config.call_count == 1
    assert outcome.state.conf.options.list_keys_only == []
    assert outcome.state.conf.options.show_core is True


def test_legacy_show_config_with_env(tox_project: ToxProjectCreator, mocker: MockerFixture) -> None:
    show_config = mocker.patch("tox.session.cmd.legacy.show_config")

    outcome = tox_project({"tox.ini": ""}).run("le", "--showconfig", "-e", "py")

    assert show_config.call_count == 1
    assert outcome.state.conf.options.list_keys_only == []
    assert outcome.state.conf.options.show_core is False


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
    assert not outcome.err
    assert not outcome.out


def test_legacy_list_env_with_no_tox_file(tox_project: ToxProjectCreator) -> None:
    project = tox_project({})
    outcome = project.run("le", "-l")
    outcome.assert_success()
    out = f"ROOT: No tox.ini or setup.cfg or pyproject.toml found, assuming empty tox.ini at {project.path}\n"
    assert not outcome.err
    assert outcome.out == out


@pytest.mark.parametrize("verbose", range(3))
def test_legacy_list_all(tox_project: ToxProjectCreator, mocker: MockerFixture, verbose: int) -> None:
    list_env = mocker.patch("tox.session.cmd.legacy.list_env")

    outcome = tox_project({"tox.ini": ""}).run("le", "-a", *(["-v"] * verbose))

    assert list_env.call_count == 1
    assert outcome.state.conf.options.list_no_description is (verbose < 1)
    assert outcome.state.conf.options.list_default_only is False
    assert outcome.state.conf.options.show_core is False


@pytest.mark.parametrize(
    "args",
    [
        pytest.param((), id="empty"),
        pytest.param(("-e", "py"), id="select"),
    ],
)
def test_legacy_devenv(
    tox_project: ToxProjectCreator,
    mocker: MockerFixture,
    tmp_path: Path,
    args: tuple[str, ...],
) -> None:
    run_sequential = mocker.patch("tox.session.cmd.devenv.run_sequential")
    into = tmp_path / "b"

    outcome = tox_project({"tox.ini": ""}).run("le", "--devenv", str(into), *args)

    assert run_sequential.call_count == 1
    assert outcome.state.conf.options.devenv_path == into
    assert set(outcome.state.conf.options.env) == {"py"}


def test_legacy_run_parallel(tox_project: ToxProjectCreator, mocker: MockerFixture) -> None:
    run_parallel = mocker.patch("tox.session.cmd.legacy.run_parallel")

    tox_project({"tox.ini": ""}).run("le", "-p", "all", "-e", "py")

    assert run_parallel.call_count == 1


def test_legacy_run_sequential(tox_project: ToxProjectCreator, mocker: MockerFixture) -> None:
    run_sequential = mocker.patch("tox.session.cmd.legacy.run_sequential")

    tox_project({"tox.ini": ""}).run("le", "-e", "py")

    assert run_sequential.call_count == 1


def test_legacy_run_sequential_ci(
    tox_project: ToxProjectCreator, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test legacy run sequential in CI by default."""
    run_sequential = mocker.patch("tox.session.cmd.legacy.run_sequential")
    monkeypatch.setenv("CI", "1")

    tox_project({"tox.ini": ""}).run("le", "-e", "py")

    assert run_sequential.call_count == 1


def test_legacy_help(tox_project: ToxProjectCreator) -> None:
    outcome = tox_project({"tox.ini": ""}).run("le", "-h")
    outcome.assert_success()


def test_legacy_cli_flags(tox_project: ToxProjectCreator, mocker: MockerFixture) -> None:
    session = mocker.MagicMock()
    session.creator.interpreter.system_executable = "I"
    virtualenv_session = mocker.patch("tox.tox_env.python.virtual_env.api.session_via_cli", return_value=session)
    ini = "[testenv]\ndeps = p>6\n c\n -rr.txt\npackage=skip\nset_env = PIP_PRE = 0"
    proj = tox_project({"tox.ini": ini})
    (proj.path / "r.txt").write_text("d")
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    args = ["--pre", "--force-dep", "p<1", "--force-dep", "b>2", "--sitepackages", "--alwayscopy"]
    result = proj.run("le", "-e", "py", *args)
    result.assert_success()

    calls = [(i[0][0].conf.name, i[0][3].run_id, i[0][3].cmd[5:]) for i in execute_calls.call_args_list]
    assert calls[0] == ("py", "install_deps", ["c", "p<1", "-r", "r.txt", "b>2"])
    for call in execute_calls.call_args_list:
        if call[0][0].name == "py":
            assert call[0][3].env["PIP_PRE"] == "1"
    assert len(virtualenv_session.call_args_list) == 1
    v_env = virtualenv_session.call_args_list[0][1]["env"]
    assert v_env["VIRTUALENV_SYSTEM_SITE_PACKAGES"] == "True"
    assert v_env["VIRTUALENV_COPIES"] == "True"
