from __future__ import annotations

from pathlib import Path

import pytest

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
        expected_args = ["python", "-I", "-m", "pip", "install"] + deps
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
def test_pyproject_deps_static_with_dynamic(
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
    proj = tox_project({"tox.ini": ""}, base=demo_pkg_inline)
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("r", "--notest", "--develop")
    result.assert_success()
    warning = (
        ".pkg: package config for py is editable, however the build backend build does not support PEP-660, "
        "falling back to editable-legacy - change your configuration to it"
    )
    assert warning in result.out.splitlines()

    expected_calls = [
        (".pkg", "_optional_hooks"),
        (".pkg", "build_wheel"),
        (".pkg", "get_requires_for_build_sdist"),
        ("py", "install_package"),
        (".pkg", "_exit"),
    ]
    found_calls = [(i[0][0].conf.name, i[0][3].run_id) for i in execute_calls.call_args_list]
    assert found_calls == expected_calls
