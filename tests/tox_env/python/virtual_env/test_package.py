import sys
from itertools import zip_longest
from textwrap import dedent

import pytest
from packaging.requirements import Requirement

from tox.pytest import TempPathFactory, ToxProjectCreator
from tox.tox_env.python.virtual_env.package.api import PackageType, Pep517VirtualEnvPackage
from tox.util.pep517.via_fresh_subprocess import SubprocessFrontend

if sys.version_info >= (3, 8):  # pragma: no cover (py38+)
    from importlib.metadata import Distribution, PathDistribution  # type: ignore[attr-defined]
else:  # pragma: no cover (<py38)
    from importlib_metadata import Distribution, PathDistribution  # noqa


@pytest.mark.parametrize(
    "pkg_type",
    ["dev", "sdist", "wheel"],
)
def test_tox_ini_package_type_valid(tox_project: ToxProjectCreator, pkg_type: str) -> None:
    proj = tox_project({"tox.ini": f"[testenv]\npackage={pkg_type}"})
    result = proj.run("c", "-k", "package_tox_env_type")
    result.assert_success()
    res = result.state.tox_env("py").conf["package"]
    assert res is getattr(PackageType, pkg_type)
    got_type = result.state.tox_env("py").conf["package_tox_env_type"]
    assert got_type == "virtualenv-pep-517"


def test_tox_ini_package_type_invalid(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": "[testenv]\npackage=bad"})
    result = proj.run("c", "-k", "package_tox_env_type")
    result.assert_failed()
    assert " invalid package config type 'bad' requested, must be one of sdist, wheel, dev, skip" in result.out


@pytest.fixture(scope="session")
def pkg_with_extras(tmp_path_factory: TempPathFactory) -> PathDistribution:  # type: ignore[no-any-unimported]
    py_ver = ".".join(str(i) for i in sys.version_info[0:2])
    setup_cfg = f"""
    [metadata]
    name = demo
    [options]
    packages = find:
    install_requires =
        appdirs>=1.4.3
        colorama>=0.4.3

    [options.extras_require]
    testing =
        covdefaults>=1.2; python_version == '2.7' or python_version == '{py_ver}'
        pytest>=5.4.1; python_version == '{py_ver}'
    docs =
        sphinx>=3
        sphinx-rtd-theme>=0.4.3,<1
    format =
        black>=3
        flake8
    """
    tmp_path = tmp_path_factory.mktemp("prj")
    (tmp_path / "setup.cfg").write_text(dedent(setup_cfg))
    (tmp_path / "setup.py").write_text("from setuptools import setup; setup()")
    toml = '[build-system]\nrequires=["setuptools", "wheel"]\nbuild-backend = "setuptools.build_meta"'
    (tmp_path / "pyproject.toml").write_text(toml)
    frontend = SubprocessFrontend(*SubprocessFrontend.create_args_from_folder(tmp_path)[:-1])
    meta = tmp_path / "meta"
    result = frontend.prepare_metadata_for_build_wheel(meta)
    return Distribution.at(result.metadata)


def test_load_dependency_no_extra(pkg_with_extras: PathDistribution) -> None:  # type: ignore[no-any-unimported]
    result = Pep517VirtualEnvPackage.discover_package_dependencies(pkg_with_extras, set())
    for left, right in zip_longest(result, (Requirement("appdirs>=1.4.3"), Requirement("colorama>=0.4.3"))):
        assert isinstance(right, Requirement)
        assert str(left) == str(right)


def test_load_dependency_many_extra(pkg_with_extras: PathDistribution) -> None:  # type: ignore[no-any-unimported]
    py_ver = ".".join(str(i) for i in sys.version_info[0:2])
    result = Pep517VirtualEnvPackage.discover_package_dependencies(pkg_with_extras, {"docs", "testing"})
    exp = [
        Requirement("appdirs>=1.4.3"),
        Requirement("colorama>=0.4.3"),
        Requirement("sphinx>=3"),
        Requirement("sphinx-rtd-theme<1,>=0.4.3"),
        Requirement(f'covdefaults>=1.2; python_version == "2.7" or python_version == "{py_ver}"'),
        Requirement(f'pytest>=5.4.1; python_version == "{py_ver}"'),
    ]
    for left, right in zip_longest(result, exp):
        assert isinstance(right, Requirement)
        assert str(left) == str(right)
