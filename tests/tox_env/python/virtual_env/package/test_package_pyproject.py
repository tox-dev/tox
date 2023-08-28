from __future__ import annotations

import json
from textwrap import dedent
from typing import TYPE_CHECKING

import pytest

from tox.execute.local_sub_process import LocalSubprocessExecuteStatus
from tox.tox_env.python.virtual_env.package.pyproject import Pep517VirtualEnvFrontend

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

    from tox.pytest import ToxProjectCreator


@pytest.mark.parametrize(
    "pkg_type",
    ["editable-legacy", "editable", "sdist", "wheel"],
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
    msg = " invalid package config type bad requested, must be one of wheel, sdist, editable, editable-legacy, skip"
    assert msg in result.out


def test_get_package_deps_different_extras(pkg_with_extras_project: Path, tox_project: ToxProjectCreator) -> None:
    ini = "[testenv:a]\npackage=editable-legacy\nextras=docs\n[testenv:b]\npackage=sdist\nextras=format"
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


@pytest.mark.parametrize(
    ("conf", "extra", "deps"),
    [
        pytest.param("[project]", "", [], id="no_deps"),
        pytest.param("[project]", "alpha", [], id="no_deps_with_extra"),
        pytest.param("[project]\ndependencies=['B', 'A']", "", ["A", "B"], id="deps"),
        pytest.param(
            "[project]\ndependencies=['A']\noptional-dependencies.alpha=['B']\noptional-dependencies.beta=['C']",
            "alpha",
            ["A", "B"],
            id="deps_with_one_extra",
        ),
        pytest.param(
            "[project]\ndependencies=['A']\noptional-dependencies.alpha=['B']\noptional-dependencies.beta=['C']",
            "alpha,beta",
            ["A", "B", "C"],
            id="deps_with_two_extra",
        ),
        pytest.param(
            "[project]\ndependencies=['A']\noptional-dependencies.alpha=[]",
            "alpha,beta",
            ["A"],
            id="deps_with_one_empty_extra",
        ),
        pytest.param(
            "[project]\ndependencies=['A']\ndynamic=['optional-dependencies']",
            "",
            ["A"],
            id="deps_with_dynamic_optional_no_extra",
        ),
        pytest.param(
            dedent(
                """
                [project]
                name='foo'
                dependencies=['foo[alpha]']
                optional-dependencies.alpha=['A']""",
            ),
            "",
            ["A"],
            id="deps_reference_extra",
        ),
        pytest.param(
            dedent(
                """
                [project]
                name='foo'
                dependencies=['A']
                optional-dependencies.alpha=['B']
                optional-dependencies.beta=['foo[alpha]']""",
            ),
            "beta",
            ["A", "B"],
            id="deps_with_recursive_extra",
        ),
        pytest.param(
            dedent(
                """
                [project]
                name='foo'
                dependencies=['A']
                optional-dependencies.alpha=['B']
                optional-dependencies.beta=['foo[alpha]']
                optional-dependencies.delta=['foo[beta]', 'D']""",
            ),
            "delta",
            ["A", "B", "D"],
            id="deps_with_two_recursive_extra",
        ),
        pytest.param(
            dedent(
                """
                [project]
                name='foo'
                optional-dependencies.alpha=['foo[beta]', 'A']
                optional-dependencies.beta=['foo[alpha]', 'B']""",
            ),
            "alpha",
            ["A", "B"],
            id="deps_with_circular_recursive_extra",
        ),
    ],
)
def test_pyproject_deps_from_static(
    tox_project: ToxProjectCreator,
    demo_pkg_inline: Path,
    conf: str,
    extra: str,
    deps: list[str],
) -> None:
    toml = f"{(demo_pkg_inline / 'pyproject.toml').read_text()}{conf}"
    proj = tox_project({"tox.ini": f"[testenv]\nextras={extra}", "pyproject.toml": toml}, base=demo_pkg_inline)
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("r", "--notest")
    result.assert_success()

    expected_calls = [(".pkg", "_optional_hooks"), (".pkg", "get_requires_for_build_sdist"), (".pkg", "build_sdist")]
    if deps:
        expected_calls.append(("py", "install_package_deps"))
    expected_calls.extend((("py", "install_package"), (".pkg", "_exit")))
    found_calls = [(i[0][0].conf.name, i[0][3].run_id) for i in execute_calls.call_args_list]
    assert found_calls == expected_calls

    if deps:
        expected_args = ["python", "-I", "-m", "pip", "install", *deps]
        args = execute_calls.call_args_list[-3][0][3].cmd
        assert expected_args == args


@pytest.mark.parametrize(
    ("metadata", "dynamic", "deps"),
    [
        pytest.param("Requires-Dist: A", "['dependencies']", ["A"], id="deps"),
        pytest.param(
            "Requires-Dist: A\nRequires-Dist: B;extra=='alpha'",
            "['dependencies']",
            ["A", "B"],
            id="deps_extra",
        ),
        pytest.param(
            "Requires-Dist: A\nRequires-Dist: B;extra=='alpha'",
            "['optional-dependencies']",
            ["A", "B"],
            id="deps_extra_dynamic_opt",
        ),
    ],
)
def test_pyproject_deps_static_with_dynamic(  # noqa: PLR0913
    tox_project: ToxProjectCreator,
    demo_pkg_inline: Path,
    monkeypatch: pytest.MonkeyPatch,
    metadata: str,
    dynamic: str,
    deps: list[str],
) -> None:
    monkeypatch.setenv("METADATA_EXTRA", metadata)
    toml = f"{(demo_pkg_inline / 'pyproject.toml').read_text()}[project]\ndynamic={dynamic}"
    ini = "[testenv]\nextras=alpha\n[testenv:.pkg]\npass_env=METADATA_EXTRA"
    proj = tox_project({"tox.ini": ini, "pyproject.toml": toml}, base=demo_pkg_inline)

    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("r", "--notest")
    result.assert_success()

    expected_calls = [
        (".pkg", "_optional_hooks"),
        (".pkg", "get_requires_for_build_sdist"),
        (".pkg", "get_requires_for_build_wheel"),
        (".pkg", "build_wheel"),
        (".pkg", "build_sdist"),
        ("py", "install_package_deps"),
        ("py", "install_package"),
        (".pkg", "_exit"),
    ]
    found_calls = [(i[0][0].conf.name, i[0][3].run_id) for i in execute_calls.call_args_list]
    assert found_calls == expected_calls

    args = execute_calls.call_args_list[-3][0][3].cmd
    assert args == ["python", "-I", "-m", "pip", "install", *deps]


def test_pyproject_no_build_editable_fallback(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    proj = tox_project({"tox.ini": "[tox]\nenv_list=a,b"}, base=demo_pkg_inline)
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("r", "-e", "a,b", "--notest", "--develop")
    result.assert_success()
    warning = (
        ".pkg: package config for a, b is editable, however the build backend build does not support PEP-660, "
        "falling back to editable-legacy - change your configuration to it"
    )
    assert warning in result.out.splitlines()

    expected_calls = [
        (".pkg", "_optional_hooks"),
        (".pkg", "get_requires_for_build_wheel"),
        (".pkg", "build_wheel"),
        (".pkg", "get_requires_for_build_sdist"),
        ("a", "install_package"),
        ("b", "install_package"),
        (".pkg", "_exit"),
    ]
    found_calls = [(i[0][0].conf.name, i[0][3].run_id) for i in execute_calls.call_args_list]
    assert found_calls == expected_calls


@pytest.mark.parametrize("package", ["sdist", "wheel", "editable", "editable-legacy", "skip"])
def test_project_package_with_deps(tox_project: ToxProjectCreator, demo_pkg_setuptools: Path, package: str) -> None:
    ini = f"[testenv]\npackage={package}\n[pkgenv]\ndeps = A"
    proj = tox_project({"tox.ini": ini}, base=demo_pkg_setuptools)
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("r", "--notest")
    result.assert_success()
    found_calls = [(i[0][0].conf.name, i[0][3].run_id) for i in execute_calls.call_args_list]
    if package == "skip":
        assert (".pkg", "install_deps") not in found_calls
    else:
        assert found_calls[0] == (".pkg", "install_requires")
        assert found_calls[1] == (".pkg", "install_deps")


def test_pyproject_build_editable_and_wheel(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    # test that build wheel and build editable are cached separately

    ini = """
    [testenv:.pkg]
    set_env= BACKEND_HAS_EDITABLE=1
    [testenv:a,b]
    package = editable
    [testenv:c,d]
    package = wheel
    """
    proj = tox_project({"tox.ini": ini}, base=demo_pkg_inline)
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)

    result = proj.run("r", "-e", "a,b,c,d", "--notest", "--workdir", str(proj.path / ".tox"))

    result.assert_success()
    found_calls = [(i[0][0].conf.name, i[0][3].run_id) for i in execute_calls.call_args_list]
    assert found_calls == [
        (".pkg", "_optional_hooks"),
        (".pkg", "get_requires_for_build_wheel"),
        (".pkg", "build_editable"),
        ("a", "install_package"),
        ("b", "install_package"),
        (".pkg", "build_wheel"),
        ("c", "install_package"),
        ("d", "install_package"),
        (".pkg", "_exit"),
    ]


def test_pyproject_config_settings_sdist(
    tox_project: ToxProjectCreator,
    demo_pkg_setuptools: Path,
    mocker: MockerFixture,
) -> None:
    ini = """
    [tox]
    env_list = sdist

    [testenv]
    wheel_build_env = .pkg
    package = sdist

    [testenv:.pkg]
    config_settings_get_requires_for_build_sdist = A = 1
    config_settings_build_sdist = B = 2
    config_settings_get_requires_for_build_wheel = C = 3
    config_settings_prepare_metadata_for_build_wheel = D = 4
    """
    proj = tox_project({"tox.ini": ini}, base=demo_pkg_setuptools)
    proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)

    write_stdin = mocker.spy(LocalSubprocessExecuteStatus, "write_stdin")

    result = proj.run("r", "--notest", from_cwd=proj.path)
    result.assert_success()

    found = {
        message["cmd"]: message["kwargs"]["config_settings"]
        for message in [json.loads(call[0][1]) for call in write_stdin.call_args_list]
        if not message["cmd"].startswith("_")
    }
    assert found == {
        "build_sdist": {"B": "2"},
        "get_requires_for_build_sdist": {"A": "1"},
        "get_requires_for_build_wheel": {"C": "3"},
        "prepare_metadata_for_build_wheel": {"D": "4"},
    }


def test_pyproject_config_settings_wheel(
    tox_project: ToxProjectCreator,
    demo_pkg_setuptools: Path,
    mocker: MockerFixture,
) -> None:
    ini = """
    [tox]
    env_list = wheel

    [testenv]
    wheel_build_env = .pkg
    package = wheel

    [testenv:.pkg]
    config_settings_get_requires_for_build_wheel = C = 3
    config_settings_prepare_metadata_for_build_wheel = D = 4
    config_settings_build_wheel = E = 5
    """
    proj = tox_project({"tox.ini": ini}, base=demo_pkg_setuptools)
    proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)

    write_stdin = mocker.spy(LocalSubprocessExecuteStatus, "write_stdin")
    mocker.patch.object(Pep517VirtualEnvFrontend, "_can_skip_prepare", return_value=False)

    result = proj.run("r", "--notest", from_cwd=proj.path)
    result.assert_success()

    found = {
        message["cmd"]: message["kwargs"]["config_settings"]
        for message in [json.loads(call[0][1]) for call in write_stdin.call_args_list]
        if not message["cmd"].startswith("_")
    }
    assert found == {
        "get_requires_for_build_wheel": {"C": "3"},
        "prepare_metadata_for_build_wheel": {"D": "4"},
        "build_wheel": {"E": "5"},
    }


def test_pyproject_config_settings_editable(
    tox_project: ToxProjectCreator,
    demo_pkg_setuptools: Path,
    mocker: MockerFixture,
) -> None:
    ini = """
    [tox]
    env_list = editable

    [testenv:.pkg]
    config_settings_get_requires_for_build_editable = F = 6
    config_settings_prepare_metadata_for_build_editable = G = 7
    config_settings_build_editable = H = 8

    [testenv]
    wheel_build_env = .pkg
    package = editable
    """
    proj = tox_project({"tox.ini": ini}, base=demo_pkg_setuptools)
    proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)

    write_stdin = mocker.spy(LocalSubprocessExecuteStatus, "write_stdin")
    mocker.patch.object(Pep517VirtualEnvFrontend, "_can_skip_prepare", return_value=False)

    result = proj.run("r", "--notest", from_cwd=proj.path)
    result.assert_success()

    found = {
        message["cmd"]: message["kwargs"]["config_settings"]
        for message in [json.loads(call[0][1]) for call in write_stdin.call_args_list]
        if not message["cmd"].startswith("_")
    }
    assert found == {
        "get_requires_for_build_editable": {"F": "6"},
        "prepare_metadata_for_build_editable": {"G": "7"},
        "build_editable": {"H": "8"},
    }


def test_pyproject_config_settings_editable_legacy(
    tox_project: ToxProjectCreator,
    demo_pkg_setuptools: Path,
    mocker: MockerFixture,
) -> None:
    ini = """
    [tox]
    env_list = editable

    [testenv:.pkg]
    config_settings_get_requires_for_build_sdist = A = 1
    config_settings_get_requires_for_build_wheel = C = 3
    config_settings_prepare_metadata_for_build_wheel = D = 4

    [testenv]
    wheel_build_env = .pkg
    package = editable-legacy
    """
    proj = tox_project({"tox.ini": ini}, base=demo_pkg_setuptools)
    proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)

    write_stdin = mocker.spy(LocalSubprocessExecuteStatus, "write_stdin")
    mocker.patch.object(Pep517VirtualEnvFrontend, "_can_skip_prepare", return_value=False)

    result = proj.run("r", "--notest", from_cwd=proj.path)
    result.assert_success()

    found = {
        message["cmd"]: message["kwargs"]["config_settings"]
        for message in [json.loads(call[0][1]) for call in write_stdin.call_args_list]
        if not message["cmd"].startswith("_")
    }
    assert found == {
        "get_requires_for_build_sdist": {"A": "1"},
        "get_requires_for_build_wheel": {"C": "3"},
        "prepare_metadata_for_build_wheel": {"D": "4"},
    }
