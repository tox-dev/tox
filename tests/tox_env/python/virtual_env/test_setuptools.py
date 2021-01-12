import os
import sys
from pathlib import Path
from typing import Optional

import pytest

from tox.pytest import ToxProjectCreator
from tox.tox_env.python.virtual_env.package.api import Pep517VirtualEnvPackage


@pytest.mark.timeout(60)
@pytest.mark.integration
def test_setuptools_package(
    tox_project: ToxProjectCreator,
    demo_pkg_setuptools: Path,
    enable_pip_pypi_access: Optional[str],  # noqa
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
    tox_env = outcome.state.tox_env("py")

    package_env = tox_env.package_env
    assert isinstance(package_env, Pep517VirtualEnvPackage)
    packages = package_env.perform_packaging("py")
    assert len(packages) == 1
    package = packages[0]
    assert package.name == f"demo_pkg_setuptools-1.2.3-py{sys.version_info.major}-none-any.whl"

    result = outcome.out.split("\n")
    py_messages = [i for i in result if "py: " in i]
    assert len(py_messages) == 6, "\n".join(py_messages)  # 1 install wheel + 3 command + 1 report + 1 final report

    package_messages = [i for i in result if ".pkg: " in i]
    # 1 install requires + 1 build requires + 1 build meta + 1 build isolated + 1 exit
    assert len(package_messages) == 5, "\n".join(package_messages)
