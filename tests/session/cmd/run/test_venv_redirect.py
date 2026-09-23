from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from tox.pytest import ToxProject, ToxProjectCreator


def _redirect(project: ToxProject) -> str:
    return (project.path / ".venv").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("env_list", "expected"),
    [
        pytest.param('[ "a", "b" ]', ".tox/a\n", id="first_of_env_list"),
        pytest.param('[ "a", "dev" ]', ".tox/dev\n", id="dev"),
    ],
)
def test_venv_redirect_default_pick(tox_project: ToxProjectCreator, env_list: str, expected: str) -> None:
    project = tox_project({"tox.toml": f"env_list = {env_list}\nno_package = true\n"})

    project.run("r", "--notest").assert_success()

    assert _redirect(project) == expected


def test_venv_redirect_prefers_editable(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    toml = 'env_list = [ "a", "b" ]\n[env.a]\npackage = "skip"\n[env.b]\npackage = "editable"\n'
    project = tox_project({"tox.toml": toml}, base=demo_pkg_inline)
    project.patch_execute(lambda request: 0 if "install" in request.run_id else None)

    project.run("r", "--notest").assert_success()

    assert _redirect(project) == ".tox/b\n"


def test_venv_redirect_skips_environment_not_created(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.toml": 'env_list = [ "a", "b" ]\nno_package = true\n'})

    project.run("r", "-e", "b", "--notest").assert_success()

    assert _redirect(project) == ".tox/b\n"


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
    project = tox_project({"tox.toml": 'env_list = [ "a" ]\nno_package = true\n', ".venv": "../shared\n"})

    project.run("r", "--notest").assert_success()

    assert _redirect(project) == "../shared\n"


def test_venv_redirect_off(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.toml": 'env_list = [ "a" ]\nno_package = true\nvenv_redirect = false\n'})

    project.run("r", "--notest").assert_success()
    project.run("r", "-r", "--notest").assert_success()

    assert not (project.path / ".venv").exists()


@pytest.mark.parametrize("recreate", [pytest.param(True, id="recreate"), pytest.param(False, id="reuse")])
def test_venv_redirect_retracted_while_recreated(tox_project: ToxProjectCreator, recreate: bool) -> None:
    project = tox_project({
        "tox.toml": 'env_list = [ "a" ]\nno_package = true\n[env_run_base]\ncommands = [ [ "python", "show.py" ] ]\n',
        "show.py": """
            import pathlib

            redirect = pathlib.Path(".venv")
            print("redirect:", redirect.read_text().strip() if redirect.exists() else "")
            """,
    })
    project.run("r").assert_success()

    outcome = project.run("r", *(["-r"] if recreate else []))

    outcome.assert_success()
    assert ("redirect: .tox/a" in outcome.out) is not recreate
    assert _redirect(project) == ".tox/a\n"
