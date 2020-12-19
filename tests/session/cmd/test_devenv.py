from typing import Optional

import pytest

from tox.pytest import ToxProjectCreator


def test_devenv_fail_multiple_target(tox_project: ToxProjectCreator) -> None:
    outcome = tox_project({"tox.ini": ""}).run("d", "-e", "py39,py38")
    outcome.assert_failed()
    msg = "ROOT: HandledError| exactly one target environment allowed in devenv mode but found py39, py38\n"
    outcome.assert_out_err(msg, "")


@pytest.mark.integration
@pytest.mark.timeout(60)
def test_devenv_ok(tox_project: ToxProjectCreator, enable_pip_pypi_access: Optional[str]) -> None:
    content = {"setup.py": "from setuptools import setup\nsetup(name='demo', version='1.0')"}
    outcome = tox_project(content).run("d", "-e", "py")
    outcome.assert_success()
