from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tox.pytest import ToxProjectCreator


def test_devenv_fail_multiple_target(tox_project: ToxProjectCreator) -> None:
    outcome = tox_project({"tox.ini": "[tox]\nenv_list=a,b"}).run("d", "-e", "a,b")
    outcome.assert_failed()
    msg = "ROOT: HandledError| exactly one target environment allowed in devenv mode but found a, b\n"
    outcome.assert_out_err(msg, "")


@pytest.mark.integration
def test_devenv_ok(tox_project: ToxProjectCreator, enable_pip_pypi_access: str | None) -> None:  # noqa: ARG001
    content = {
        "setup.py": "from setuptools import setup\nsetup(name='demo', version='1.0')",
        "tox.ini": "[tox]\nenv_list = py\n[testenv]\nusedevelop = True",
    }
    project = tox_project(content)
    outcome = project.run("d", "-e", "py")

    outcome.assert_success()
    assert (project.path / "venv").exists()
    assert f"created development environment under {project.path / 'venv'}" in outcome.out


def test_devenv_help(tox_project: ToxProjectCreator) -> None:
    outcome = tox_project({"tox.ini": ""}).run("d", "-h")
    outcome.assert_success()
