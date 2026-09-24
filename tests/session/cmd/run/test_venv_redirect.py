from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from tox.pytest import ToxProject, ToxProjectCreator


def _redirect(project: ToxProject) -> str:
    return (project.path / ".venv").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("config", "expected"),
    [
        pytest.param('env_list = [ "a", "dev" ]', ".tox/dev\n", id="dev"),
        pytest.param('env_list = [ "dev" ]\nvenv_redirect = true', ".tox/dev\n", id="explicit_true"),
    ],
)
def test_venv_redirect_default_pick(tox_project: ToxProjectCreator, config: str, expected: str) -> None:
    project = tox_project({"tox.toml": f"{config}\nno_package = true\n"})

    project.run("r", "--notest").assert_success()

    assert _redirect(project) == expected


def test_venv_redirect_prefers_editable(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    toml = 'env_list = [ "a", "b" ]\n[env.a]\npackage = "skip"\n[env.b]\npackage = "editable"\n'
    project = tox_project({"tox.toml": toml}, base=demo_pkg_inline)
    project.patch_execute(lambda request: 0 if "install" in request.run_id else None)

    project.run("r", "--notest").assert_success()

    assert _redirect(project) == ".tox/b\n"


@pytest.mark.parametrize(
    ("env_list", "run"),
    [
        pytest.param('[ "a", "b" ]', "a,b", id="no_dev_or_develop_env"),
        pytest.param('[ "a", "dev" ]', "a", id="dev_not_created_yet"),
    ],
)
def test_venv_redirect_writes_nothing_without_the_chosen_env(
    tox_project: ToxProjectCreator, env_list: str, run: str
) -> None:
    project = tox_project({"tox.toml": f"env_list = {env_list}\nno_package = true\n"})

    project.run("r", "-e", run, "--notest").assert_success()

    assert not (project.path / ".venv").exists()


def test_venv_redirect_env_pins_environment(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.toml": 'env_list = [ "a", "dev" ]\nno_package = true\nvenv_redirect_env = "a"\n'})

    project.run("r", "--notest").assert_success()

    assert _redirect(project) == ".tox/a\n"


def test_venv_redirect_env_not_created_writes_nothing(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.toml": 'env_list = [ "a", "b" ]\nno_package = true\nvenv_redirect_env = "b"\n'})

    project.run("r", "-e", "a", "--notest").assert_success()

    assert not (project.path / ".venv").exists()


def test_venv_redirect_env_unknown_warns(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.toml": 'env_list = [ "a" ]\nno_package = true\nvenv_redirect_env = "nope"\n'})

    outcome = project.run("r", "--notest")

    outcome.assert_success()
    assert "venv_redirect_env names nope, which is not a tox environment" in outcome.out


def test_venv_redirect_keeps_foreign_redirect(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.toml": 'env_list = [ "dev" ]\nno_package = true\n', ".venv": "../shared\n"})

    project.run("r", "--notest").assert_success()

    assert _redirect(project) == "../shared\n"


def test_venv_redirect_off(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.toml": 'env_list = [ "dev" ]\nno_package = true\nvenv_redirect = false\n'})

    project.run("r", "--notest").assert_success()
    project.run("r", "-r", "--notest").assert_success()

    assert not (project.path / ".venv").exists()


@pytest.mark.parametrize("recreate", [pytest.param(True, id="recreate"), pytest.param(False, id="reuse")])
def test_venv_redirect_retracted_while_recreated(tox_project: ToxProjectCreator, recreate: bool) -> None:
    project = tox_project({
        "tox.toml": 'env_list = [ "dev" ]\nno_package = true\n[env_run_base]\ncommands = [ [ "python", "show.py" ] ]\n',
        "show.py": """
            import pathlib

            redirect = pathlib.Path(".venv")
            print("redirect:", redirect.read_text().strip() if redirect.exists() else "")
            """,
    })
    project.run("r").assert_success()

    outcome = project.run("r", *(["-r"] if recreate else []))

    outcome.assert_success()
    assert ("redirect: .tox/dev" in outcome.out) is not recreate
    assert _redirect(project) == ".tox/dev\n"


@pytest.fixture
def dot_venv_env_project(tox_project: ToxProjectCreator) -> ToxProject:
    return tox_project({
        "tox.toml": """
            env_list = [ "lint" ]
            no_package = true
            [env.dev]
            env_dir = "{tox_root}{/}.venv"
            """,
    })


def test_venv_redirect_off_while_an_environment_lives_at_dot_venv(dot_venv_env_project: ToxProject) -> None:
    dot_venv_env_project.run("r", "-e", "lint", "--notest").assert_success()

    assert not (dot_venv_env_project.path / ".venv").exists()


def test_venv_redirect_environment_at_dot_venv_builds_after_another_ran(dot_venv_env_project: ToxProject) -> None:
    dot_venv_env_project.run("r", "-e", "lint", "--notest").assert_success()

    dot_venv_env_project.run("r", "-e", "dev", "--notest").assert_success()

    assert (dot_venv_env_project.path / ".venv" / "pyvenv.cfg").is_file()


def test_venv_redirect_left_by_tox_makes_way_for_environment_at_dot_venv(dot_venv_env_project: ToxProject) -> None:
    (dot_venv_env_project.path / ".venv").write_text(".tox/lint\n", encoding="utf-8")

    dot_venv_env_project.run("r", "-e", "dev", "--notest").assert_success()

    assert (dot_venv_env_project.path / ".venv" / "pyvenv.cfg").is_file()


def test_venv_redirect_foreign_file_in_env_dir_fails_the_environment(dot_venv_env_project: ToxProject) -> None:
    (dot_venv_env_project.path / ".venv").write_text("../shared\n", encoding="utf-8")

    outcome = dot_venv_env_project.run("r", "-e", "dev", "--notest")

    outcome.assert_failed(code=1)
    assert "is a file where this environment should live and not a redirect tox wrote; delete it" in outcome.out


def test_venv_redirect_true_conflicts_with_environment_at_dot_venv(dot_venv_env_project: ToxProject) -> None:
    outcome = dot_venv_env_project.run("r", "-e", "lint", "--notest", "-x", "venv_redirect=true")

    outcome.assert_failed(code=-2)
    assert "venv_redirect is true, but tox environment dev lives at" in outcome.out


@pytest.fixture
def devenv_project(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> ToxProject:
    project = tox_project({"tox.toml": 'env_list = [ "dev" ]\n[env.dev]\npackage = "skip"\n'}, base=demo_pkg_inline)
    project.patch_execute(lambda request: 0 if "install" in request.run_id else None)
    return project


def test_venv_redirect_devenv_points_at_created_env(devenv_project: ToxProject) -> None:
    devenv_project.run("d", "-e", "py", "work").assert_success()

    assert _redirect(devenv_project) == "work\n"


def test_venv_redirect_devenv_replaces_foreign_redirect(devenv_project: ToxProject) -> None:
    (devenv_project.path / ".venv").write_text("../shared\n", encoding="utf-8")

    devenv_project.run("d", "-e", "py", "work").assert_success()

    assert _redirect(devenv_project) == "work\n"


def test_venv_redirect_run_keeps_devenv_redirect(devenv_project: ToxProject) -> None:
    devenv_project.run("d", "-e", "py", "work").assert_success()

    devenv_project.run("r", "-e", "dev", "--notest").assert_success()

    assert _redirect(devenv_project) == "work\n"


def test_venv_redirect_off_silences_devenv(devenv_project: ToxProject) -> None:
    devenv_project.run("d", "-e", "py", "work", "-x", "venv_redirect=false").assert_success()

    assert not (devenv_project.path / ".venv").exists()


def test_venv_redirect_virtualenv_writes_none_beside_tox_environments(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.toml": 'env_list = [ "a" ]\nno_package = true\n'})

    project.run("r", "--notest").assert_success()

    assert not (project.path / ".tox" / ".venv").exists()
