import sys
from itertools import zip_longest
from pathlib import Path
from textwrap import dedent

import pytest
from packaging.requirements import Requirement

from tox.pytest import TempPathFactory, ToxProjectCreator
from tox.tox_env.python.virtual_env.package.api import Pep517VirtualEnvPackage
from tox.util.pep517.via_fresh_subprocess import SubprocessFrontend

if sys.version_info >= (3, 8):  # pragma: no cover (py38+)
    from importlib.metadata import Distribution, PathDistribution  # type: ignore[attr-defined]
else:  # pragma: no cover (<py38)
    from importlib_metadata import Distribution, PathDistribution


@pytest.mark.parametrize(
    "pkg_type",
    ["dev-legacy", "sdist", "wheel"],
)
def test_tox_ini_package_type_valid(tox_project: ToxProjectCreator, pkg_type: str) -> None:
    proj = tox_project({"tox.ini": f"[testenv]\npackage={pkg_type}"})
    result = proj.run("c", "-k", "package_tox_env_type")
    result.assert_success()
    res = result.env_conf("py")["package"]
    assert res == pkg_type
    got_type = result.env_conf("py")["package_tox_env_type"]
    assert got_type == "virtualenv-pep-517"


def test_tox_ini_package_type_invalid(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": "[testenv]\npackage=bad"})
    result = proj.run("c", "-k", "package_tox_env_type")
    result.assert_failed()
    assert " invalid package config type bad requested, must be one of wheel, sdist, dev-legacy, skip" in result.out


@pytest.fixture(scope="session")
def pkg_with_extras_project(tmp_path_factory: TempPathFactory) -> Path:
    py_ver = ".".join(str(i) for i in sys.version_info[0:2])
    setup_cfg = f"""
    [metadata]
    name = demo
    [options]
    packages = find:
    install_requires =
        platformdirs>=2.1
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
    return tmp_path


@pytest.fixture(scope="session")
def pkg_with_extras(pkg_with_extras_project: Path) -> PathDistribution:  # type: ignore[no-any-unimported]
    frontend = SubprocessFrontend(*SubprocessFrontend.create_args_from_folder(pkg_with_extras_project)[:-1])
    meta = pkg_with_extras_project / "meta"
    result = frontend.prepare_metadata_for_build_wheel(meta)
    return Distribution.at(result.metadata)


def test_load_dependency_no_extra(pkg_with_extras: PathDistribution) -> None:  # type: ignore[no-any-unimported]
    result = Pep517VirtualEnvPackage._dependencies_with_extras(
        [Requirement(i) for i in pkg_with_extras.requires], set()
    )
    for left, right in zip_longest(result, (Requirement("platformdirs>=2.1"), Requirement("colorama>=0.4.3"))):
        assert isinstance(right, Requirement)
        assert str(left) == str(right)


def test_load_dependency_many_extra(pkg_with_extras: PathDistribution) -> None:  # type: ignore[no-any-unimported]
    py_ver = ".".join(str(i) for i in sys.version_info[0:2])
    result = Pep517VirtualEnvPackage._dependencies_with_extras(
        [Requirement(i) for i in pkg_with_extras.requires], {"docs", "testing"}
    )
    exp = [
        Requirement("platformdirs>=2.1"),
        Requirement("colorama>=0.4.3"),
        Requirement("sphinx>=3"),
        Requirement("sphinx-rtd-theme<1,>=0.4.3"),
        Requirement(f'covdefaults>=1.2; python_version == "2.7" or python_version == "{py_ver}"'),
        Requirement(f'pytest>=5.4.1; python_version == "{py_ver}"'),
    ]
    for left, right in zip_longest(result, exp):
        assert isinstance(right, Requirement)
        assert str(left) == str(right)


def test_get_package_deps_different_extras(pkg_with_extras_project: Path, tox_project: ToxProjectCreator) -> None:
    ini = "[testenv:a]\npackage=dev-legacy\nextras=docs\n[testenv:b]\npackage=sdist\nextras=format"
    proj = tox_project({"tox.ini": ini})
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("r", "--root", str(pkg_with_extras_project), "-e", "a,b")
    result.assert_success()
    installs = {
        i[0][0].conf.name: i[0][3].cmd[5:]
        for i in execute_calls.call_args_list
        if i[0][3].run_id.startswith("install_package_deps")
    }
    assert installs == {
        "a": ["colorama>=0.4.3", "platformdirs>=2.1", "setuptools", "sphinx-rtd-theme<1,>=0.4.3", "sphinx>=3", "wheel"],
        "b": ["black>=3", "colorama>=0.4.3", "flake8", "platformdirs>=2.1"],
    }


def test_package_root_via_root(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    ini = f"[tox]\npackage_root={demo_pkg_inline}\n[testenv]\npackage=wheel\nwheel_build_env=.pkg"
    proj = tox_project({"tox.ini": ini})
    proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("r", "--notest")
    result.assert_success()


def test_package_root_via_testenv(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    ini = f"[testenv]\npackage=wheel\nwheel_build_env=.pkg\npackage_root={demo_pkg_inline}"
    proj = tox_project({"tox.ini": ini})
    proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("r", "--notest")
    result.assert_success()
