from __future__ import annotations

from typing import TYPE_CHECKING, Callable
from zipfile import ZipFile

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from tox.pytest import ToxProjectCreator


@pytest.fixture(scope="session")
def pkg_with_extras_project_wheel(
    pkg_with_extras_project: Path,
    pkg_builder: Callable[[Path, Path, list[str], bool], Path],
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


@pytest.fixture(scope="session")
def pkg_with_sdist(
    pkg_with_extras_project: Path,
    pkg_builder: Callable[[Path, Path, list[str], bool], Path],
) -> Path:
    dist = pkg_with_extras_project / "dist"
    pkg_builder(dist, pkg_with_extras_project, ["sdist"], False)
    return next(dist.iterdir())


@pytest.fixture
def pkg_with_extras_project_sdist(
    pkg_with_extras_project: Path,
    pkg_builder: Callable[[Path, Path, list[str], bool], Path],
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
        (".pkg_external_sdist_meta", "_optional_hooks", []),
        (".pkg_external_sdist_meta", "get_requires_for_build_sdist", []),
        (".pkg_external_sdist_meta", "get_requires_for_build_wheel", []),  # required before prepare_metadata*
        (".pkg_external_sdist_meta", "prepare_metadata_for_build_wheel", []),
        ("py", "install_package_deps", deps),
        ("py", "install_package", ["--force-reinstall", "--no-deps", str(pkg_with_extras_project_sdist)]),
    ]


@pytest.mark.parametrize("mode", ["p", "le"])  # no need for r as is tested above
def test_install_pkg_via(tox_project: ToxProjectCreator, mode: str, pkg_with_extras_project_wheel: Path) -> None:
    proj = tox_project({"tox.ini": "[testenv]\npackage=wheel"})
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)

    result = proj.run(mode, "--installpkg", str(pkg_with_extras_project_wheel))

    result.assert_success()
    calls = [(i[0][0].conf.name, i[0][3].run_id) for i in execute_calls.call_args_list]
    assert calls == [("py", "install_package_deps"), ("py", "install_package")]


@pytest.mark.usefixtures("enable_pip_pypi_access")
def test_build_wheel_external(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    ini = """
    [testenv]
    package = external
    package_env = .ext
    commands =
        python -c 'from demo_pkg_inline import do; do()'

    [testenv:.ext]
    deps = build
    package_glob = {envtmpdir}{/}dist{/}*.whl
    commands =
        pyproject-build -w . -o {envtmpdir}{/}dist
    """
    project = tox_project({"tox.ini": ini})
    result = project.run("r", "--root", str(demo_pkg_inline), "--workdir", str(project.path))

    result.assert_success()
    assert "greetings from demo_pkg_inline" in result.out


def test_build_wheel_external_fail_build(tox_project: ToxProjectCreator) -> None:
    ini = """
    [testenv]
    package = external
    [testenv:.pkg_external]
    commands = xyz
    """
    project = tox_project({"tox.ini": ini})
    result = project.run("r")

    result.assert_failed()
    assert "stopping as failed to build package" in result.out, result.out


def test_build_wheel_external_fail_no_pkg(tox_project: ToxProjectCreator) -> None:
    ini = """
    [testenv]
    package = external
    """
    project = tox_project({"tox.ini": ini})
    result = project.run("r")

    result.assert_failed()
    assert "failed with no package found in " in result.out, result.out


def test_build_wheel_external_fail_many_pkg(tox_project: ToxProjectCreator) -> None:
    ini = """
    [testenv]
    package = external
    [testenv:.pkg_external]
    commands =
        python -c 'from pathlib import Path; (Path(r"{env_tmp_dir}") / "dist").mkdir()'
        python -c 'from pathlib import Path; (Path(r"{env_tmp_dir}") / "dist" / "a").write_text("")'
        python -c 'from pathlib import Path; (Path(r"{env_tmp_dir}") / "dist" / "b").write_text("")'
    """
    project = tox_project({"tox.ini": ini})
    result = project.run("r")

    result.assert_failed()
    assert "failed with found more than one package " in result.out, result.out


def test_tox_install_pkg_bad_wheel(tox_project: ToxProjectCreator, tmp_path: Path) -> None:
    wheel = tmp_path / "w.whl"
    with ZipFile(str(wheel), "w"):
        pass
    proj = tox_project({"tox.ini": "[testenv]"})
    result = proj.run("r", "-e", "py", "--installpkg", str(wheel))

    result.assert_failed()
    assert "failed with no .dist-info inside " in result.out, result.out


def test_tox_install_pkg_with_skip_install(
    tox_project: ToxProjectCreator,
    demo_pkg_inline: Path,
    demo_pkg_inline_wheel: Path,
) -> None:
    ini = "[testenv:foo]\nskip_install = true"
    project = tox_project({"tox.ini": ini, "pyproject.toml": (demo_pkg_inline / "pyproject.toml").read_text()})
    result = project.run("-e", "py", "--installpkg", str(demo_pkg_inline_wheel))
    result.assert_success()


def test_run_installpkg_targz(
    tox_project: ToxProjectCreator,
    pkg_with_sdist: Path,
    enable_pip_pypi_access: str | None,  # noqa: ARG001
) -> None:
    project = tox_project({
        "tox.ini": """
     [tox]
    envlist = base, flake8
    [testenv]
    package = sdist
    [testenv:base]
    [testenv:flake8]
    """
    })
    outcome = project.run(f"--installpkg={pkg_with_sdist}")
    outcome.assert_success()
