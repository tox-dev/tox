import sys
from pathlib import Path
from typing import List, Sequence

import pytest
import setuptools
import wheel

from tox.execute.api import Outcome
from tox.execute.request import ExecuteRequest
from tox.pytest import ToxProjectCreator
from tox.tox_env.python.virtual_env.api import VirtualEnv
from tox.tox_env.python.virtual_env.package.artifact.wheel import Pep517VirtualEnvPackageWheel


@pytest.fixture()
def use_host_virtualenv(monkeypatch):
    # disable install
    def perform_install(self, install_command: Sequence[str]) -> Outcome:
        install_command = ("python", "-c", "import sys; print(sys.argv)") + tuple(install_command)
        return old_cmd(self, install_command)

    old_cmd = VirtualEnv.perform_install
    monkeypatch.setattr(VirtualEnv, "perform_install", perform_install)

    # return hots path
    def paths(self) -> List[Path]:
        return [Path(sys.executable).parent]

    monkeypatch.setattr(VirtualEnv, "paths", paths)

    # return hots path
    def create_python_env(self):
        return Outcome(ExecuteRequest(["a"], Path(), {}, False), False, Outcome.OK, "", "", 0, 1.0, ["a"])

    monkeypatch.setattr(VirtualEnv, "create_python_env", create_python_env)


def test_setuptools_package_wheel_universal(tox_project: ToxProjectCreator, use_host_virtualenv):
    project = tox_project(
        {
            "tox.ini": """
                    [tox]
                    env_list = py

                    [testenv]
                    package = wheel
                    """,
            "setup.cfg": """
                    [metadata]
                    name = magic
                    version = 1.2.3
                    [options]
                    packages = find:
                    package_dir =
                        =src
                    [options.packages.find]
                    where = src
                    [bdist_wheel]
                    universal = 1
                """,
            "pyproject.toml": f"""
                    [build-system]
                    requires = [
                        "setuptools >= {setuptools.__version__}",
                        "wheel >= {wheel.__version__}",
                    ]
                    build-backend = 'setuptools.build_meta'
                 """,
            "src": {"magic": {"__init__.py": """__version__ = "1.2.3" """}},
        },
    )
    outcome = project.run("r")
    tox_env = outcome.state.tox_envs["py"]
    package_env = tox_env.package_env
    assert isinstance(package_env, Pep517VirtualEnvPackageWheel)
    packages = package_env.perform_packaging()
    assert len(packages) == 1
    package = packages[0]
    assert package.name == "magic-1.2.3-py2.py3-none-any.whl"

    result = outcome.out.split("\n")
    py_messages = [i for i in result if "py: " in i]
    assert len(py_messages) == 2  # 1 install wheel + 1 report

    package_messages = [i for i in result if ".package: " in i]
    # 1 install requires + 1 build requires + 1 build meta + 1 build isolated
    assert len(package_messages) == 4
