from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING, cast

import pytest

from tox.tox_env.python.package import WheelPackage
from tox.tox_env.python.virtual_env.package.pyproject import Pep517VirtualEnvPackager
from tox.tox_env.runner import RunToxEnv

if TYPE_CHECKING:
    from pathlib import Path

    from tox.pytest import ToxProjectCreator


@pytest.mark.integration
def test_setuptools_package(
    tox_project: ToxProjectCreator,
    demo_pkg_setuptools: Path,
    enable_pip_pypi_access: str | None,  # noqa: ARG001
) -> None:
    tox_ini = """
        [testenv]
        package = wheel
        commands_pre = python -c 'import sys; print("start", sys.executable)'
        commands = python -c 'from demo_pkg_setuptools import do; do()'
        commands_post = python -c 'import sys; print("end", sys.executable)'
    """
    project = tox_project({"tox.ini": tox_ini}, base=demo_pkg_setuptools)

    outcome = project.run("r", "-e", "py")

    outcome.assert_success()
    assert f"\ngreetings from demo_pkg_setuptools{os.linesep}" in outcome.out
    tox_env = cast(RunToxEnv, outcome.state.envs["py"])

    (package_env,) = list(tox_env.package_envs)
    assert isinstance(package_env, Pep517VirtualEnvPackager)
    packages = package_env.perform_packaging(tox_env.conf)
    assert len(packages) == 1
    package = packages[0]
    assert isinstance(package, WheelPackage)
    assert str(package) == str(package.path)
    assert package.path.name == f"demo_pkg_setuptools-1.2.3-py{sys.version_info.major}-none-any.whl"

    result = outcome.out.split("\n")
    py_messages = [i for i in result if "py: " in i]
    assert len(py_messages) == 5, "\n".join(py_messages)  # 1 install wheel + 3 command + 1 final report

    package_messages = [i for i in result if ".pkg: " in i]
    # 1 optional hooks + 1 install requires + 1 build meta + 1 build isolated
    assert len(package_messages) == 4, "\n".join(package_messages)
