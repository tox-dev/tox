from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from tox.pytest import ToxProject, ToxProjectCreator


def _catalog(project: ToxProject) -> list[str]:
    return (project.path / ".python-envs").read_text(encoding="utf-8").splitlines()


def test_python_envs_default_is_first_of_env_list(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.toml": 'env_list = [ "a", "b" ]\nno_package = true\n'})

    project.run("r", "--notest").assert_success()

    assert _catalog(project) == [f".tox{os.sep}b", f".tox{os.sep}a"]


def test_python_envs_default_is_dev(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.toml": 'env_list = [ "a", "dev" ]\nno_package = true\n'})

    project.run("r", "--notest").assert_success()

    assert _catalog(project) == [f".tox{os.sep}a", f".tox{os.sep}dev"]


def test_python_envs_default_is_editable(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    toml = 'env_list = [ "a", "b" ]\n[env.a]\npackage = "skip"\n[env.b]\npackage = "editable"\n'
    project = tox_project({"tox.toml": toml}, base=demo_pkg_inline)
    project.patch_execute(lambda request: 0 if "install" in request.run_id else None)

    project.run("r", "--notest").assert_success()

    assert _catalog(project) == [f".tox{os.sep}a", f".tox{os.sep}b"]


def test_python_envs_skips_environment_not_created(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.toml": 'env_list = [ "a", "b" ]\nno_package = true\n'})

    project.run("r", "-e", "a", "--notest").assert_success()

    assert _catalog(project) == [f".tox{os.sep}a"]


def test_python_envs_off(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.toml": 'env_list = [ "a" ]\nno_package = true\npython_envs = false\n'})

    project.run("r", "--notest").assert_success()
    project.run("r", "-r", "--notest").assert_success()

    assert not (project.path / ".python-envs").exists()


@pytest.mark.parametrize("recreate", [pytest.param(True, id="recreate"), pytest.param(False, id="reuse")])
def test_python_envs_forgotten_while_recreated(tox_project: ToxProjectCreator, recreate: bool) -> None:
    project = tox_project({
        "tox.toml": 'env_list = [ "a" ]\nno_package = true\n[env_run_base]\ncommands = [ [ "python", "show.py" ] ]\n',
        "show.py": """
            import pathlib

            catalog = pathlib.Path(".python-envs")
            print("catalog:", *(catalog.read_text().split() if catalog.exists() else ()))
            """,
    })
    project.run("r").assert_success()

    outcome = project.run("r", *(["-r"] if recreate else []))

    outcome.assert_success()
    assert (f"catalog: .tox{os.sep}a" in outcome.out) is not recreate
