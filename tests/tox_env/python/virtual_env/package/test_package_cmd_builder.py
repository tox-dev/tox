from pathlib import Path
from typing import Callable, List

import pytest

from tox.pytest import ToxProjectCreator


@pytest.fixture(scope="session")
def pkg_with_extras_project_wheel(
    pkg_with_extras_project: Path, pkg_builder: Callable[[Path, Path, List[str], bool], Path]
) -> Path:
    dist = pkg_with_extras_project / "dist"
    pkg_builder(dist, pkg_with_extras_project, ["wheel"], False)
    return next(dist.iterdir())


def test_tox_install_pkg_wheel(tox_project: ToxProjectCreator, pkg_with_extras_project_wheel: Path) -> None:
    proj = tox_project({"tox.ini": "[testenv]\nextras=docs,format"})
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("r", "-e", "py", "--installpkg", str(pkg_with_extras_project_wheel))
    result.assert_success()
    calls = [(i[0][0].conf.name, i[0][3].run_id, i[0][3].cmd[5:]) for i in execute_calls.call_args_list]
    deps = ["black>=3", "colorama>=0.4.3", "flake8", "platformdirs>=2.1", "sphinx-rtd-theme<1,>=0.4.3", "sphinx>=3"]
    expected = [
        ("py", "install_package_deps", deps),
        ("py", "install_package", ["--force-reinstall", "--no-deps", str(pkg_with_extras_project_wheel)]),
    ]
    assert calls == expected


@pytest.fixture()
def pkg_with_extras_project_sdist(
    pkg_with_extras_project: Path, pkg_builder: Callable[[Path, Path, List[str], bool], Path]
) -> Path:
    dist = pkg_with_extras_project / "sdist"
    pkg_builder(dist, pkg_with_extras_project, ["sdist"], False)
    return next(dist.iterdir())


def test_tox_install_pkg_sdist(tox_project: ToxProjectCreator, pkg_with_extras_project_sdist: Path) -> None:
    proj = tox_project({"tox.ini": "[testenv]\nextras=docs,format"})
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("r", "-e", "py", "--installpkg", str(pkg_with_extras_project_sdist))
    result.assert_success()
    calls = [(i[0][0].conf.name, i[0][3].run_id, i[0][3].cmd[5:]) for i in execute_calls.call_args_list]
    deps = ["black>=3", "colorama>=0.4.3", "flake8", "platformdirs>=2.1", "sphinx-rtd-theme<1,>=0.4.3", "sphinx>=3"]
    assert calls == [
        (".pkg_external_sdist_meta", "install_requires", ["setuptools", "wheel"]),
        (".pkg_external_sdist_meta", "get_requires_for_build_sdist", []),
        (".pkg_external_sdist_meta", "prepare_metadata_for_build_wheel", []),
        ("py", "install_package_deps", deps),
        ("py", "install_package", ["--force-reinstall", "--no-deps", str(pkg_with_extras_project_sdist)]),
        (".pkg_external_sdist_meta", "_exit", []),
    ]


@pytest.mark.parametrize("mode", ["p", "le"])  # no need for r as is tested above
def test_install_pkg_via(tox_project: ToxProjectCreator, mode: str, pkg_with_extras_project_wheel: Path) -> None:
    proj = tox_project({"tox.ini": "[testenv]\npackage=wheel"})
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)

    result = proj.run(mode, "--installpkg", str(pkg_with_extras_project_wheel))

    result.assert_success()
    calls = [(i[0][0].conf.name, i[0][3].run_id) for i in execute_calls.call_args_list]
    assert calls == [("py", "install_package_deps"), ("py", "install_package")]
