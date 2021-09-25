from pathlib import Path

import pytest

from tox.pytest import ToxProjectCreator


@pytest.mark.parametrize(
    "pkg_type",
    ["dev-legacy", "sdist", "wheel"],
)
def test_tox_ini_package_type_valid(tox_project: ToxProjectCreator, pkg_type: str) -> None:
    proj = tox_project({"tox.ini": f"[testenv]\npackage={pkg_type}", "pyproject.toml": ""})
    result = proj.run("c", "-k", "package_tox_env_type")
    result.assert_success()
    res = result.env_conf("py")["package"]
    assert res == pkg_type
    got_type = result.env_conf("py")["package_tox_env_type"]
    assert got_type == "virtualenv-pep-517"


def test_tox_ini_package_type_invalid(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": "[testenv]\npackage=bad", "pyproject.toml": ""})
    result = proj.run("c", "-k", "package_tox_env_type")
    result.assert_failed()
    assert " invalid package config type bad requested, must be one of wheel, sdist, dev-legacy, skip" in result.out


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
    proj = tox_project({"tox.ini": ini, "pyproject.toml": ""})
    proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("r", "--notest")
    result.assert_success()


def test_package_root_via_testenv(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    ini = f"[testenv]\npackage=wheel\nwheel_build_env=.pkg\npackage_root={demo_pkg_inline}"
    proj = tox_project({"tox.ini": ini, "pyproject.toml": ""})
    proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("r", "--notest")
    result.assert_success()
