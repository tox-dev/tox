import pytest

from tox.pytest import ToxProjectCreator
from tox.tox_env.python.virtual_env.package.api import PackageType


@pytest.mark.parametrize(
    "pkg_type, of_type",
    [
        ("dev", "virtualenv-legacy-dev"),
        ("sdist", "virtualenv-pep-517-sdist"),
        ("wheel", "virtualenv-pep-517-wheel"),
    ],
)
def test_tox_ini_package_type_valid(tox_project: ToxProjectCreator, pkg_type: str, of_type: str) -> None:
    proj = tox_project({"tox.ini": f"[testenv]\npackage={pkg_type}"})
    result = proj.run("c", "-k", "package_tox_env_type")
    result.assert_success()
    res = result.state.tox_env("py").conf["package"]
    assert res is getattr(PackageType, pkg_type)
    got_type = result.state.tox_env("py").conf["package_tox_env_type"]
    assert got_type == of_type


def test_tox_ini_package_type_invalid(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": "[testenv]\npackage=bad"})
    result = proj.run("c", "-k", "package_tox_env_type")
    result.assert_failed()
    assert " invalid package config type 'bad' requested, must be one of sdist, wheel, dev, skip" in result.out
