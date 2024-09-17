from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import TYPE_CHECKING, Callable
from unittest.mock import patch

import pytest

from tox.tox_env.errors import Fail
from tox.tox_env.python.api import Python

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

    from tox.pytest import ToxProjectCreator


def test_requirements_txt(tox_project: ToxProjectCreator) -> None:
    prj = tox_project(
        {
            "tox.ini": "[testenv]\npackage=skip\ndeps=-rrequirements.txt",
            "requirements.txt": "nose",
        },
    )
    execute_calls = prj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = prj.run("r", "-e", "py")
    result.assert_success()

    assert execute_calls.call_count == 1
    exp = ["python", "-I", "-m", "pip", "install", "-r", "requirements.txt"]
    got_cmd = execute_calls.call_args[0][3].cmd

    assert got_cmd == exp


def test_conflicting_base_python_factor() -> None:
    major, minor = sys.version_info[0:2]
    name = f"py{major}{minor}-py{major}{minor - 1}"
    with pytest.raises(ValueError, match=f"conflicting factors py{major}{minor}, py{major}{minor - 1} in {name}"):
        Python.extract_base_python(name)


def test_build_wheel_in_non_base_pkg_env(
    tox_project: ToxProjectCreator,
    patch_prev_py: Callable[[bool], tuple[str, str]],
    demo_pkg_inline: Path,
    mocker: MockerFixture,
) -> None:
    mocker.patch("tox.tox_env.python.virtual_env.api.session_via_cli")
    prev_ver, impl = patch_prev_py(True)
    prev_py = f"py{prev_ver}"
    prj = tox_project({"tox.ini": f"[tox]\nenv_list= {prev_py}\n[testenv]\npackage=wheel"})
    execute_calls = prj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = prj.run("-r", "--root", str(demo_pkg_inline))
    result.assert_success()
    calls = [(i[0][0].conf.name, i[0][3].run_id) for i in execute_calls.call_args_list]
    assert calls == [
        (f".pkg-{impl}{prev_ver}", "_optional_hooks"),
        (f".pkg-{impl}{prev_ver}", "get_requires_for_build_wheel"),
        (f".pkg-{impl}{prev_ver}", "build_wheel"),
        (f"py{prev_ver}", "install_package"),
        (f".pkg-{impl}{prev_ver}", "_exit"),
    ]


def test_diff_msg_added_removed_changed() -> None:
    before = {"A": "1", "F": "8", "C": "3", "D": "4", "E": "6"}
    after = {"G": "9", "B": "2", "C": "3", "D": "5", "E": "7"}
    expected = "python added A='1' | F='8', removed G='9' | B='2', changed D='5'->'4' | E='7'->'6'"
    assert Python._diff_msg(before, after) == expected  # noqa: SLF001


def test_diff_msg_no_diff() -> None:
    assert Python._diff_msg({}, {}) == "python "  # noqa: SLF001


@pytest.mark.parametrize(
    ("env", "base_python"),
    [
        ("py3", "py3"),
        ("py311", "py311"),
        ("py3.12", "py3.12"),
        ("pypy2", "pypy2"),
        ("rustpython3", "rustpython3"),
        ("graalpy", "graalpy"),
        ("jython", "jython"),
        ("cpython3.8", "cpython3.8"),
        ("ironpython2.7", "ironpython2.7"),
        ("functional-py310", "py310"),
        ("bar-pypy2-foo", "pypy2"),
        ("py", None),
        ("django-32", None),
        ("eslint-8.3", None),
        ("py-310", None),
        ("py3000", None),
        ("4.foo", None),
        ("310", None),
        ("5", None),
        ("2000", None),
        ("4000", None),
        ("3.10", "3.10"),
        ("3.9", "3.9"),
        ("2.7", "2.7"),
        ("pypy-3.10", "pypy3.10"),
    ],
    ids=lambda a: "|".join(a) if isinstance(a, list) else str(a),
)
def test_extract_base_python(env: str, base_python: str | None) -> None:
    result = Python.extract_base_python(env)
    assert result == base_python


@pytest.mark.parametrize("ignore_conflict", [True, False])
@pytest.mark.parametrize(
    ("env", "base_python"),
    [
        ("magic", ["pypy"]),
        ("magic", ["py39"]),
    ],
    ids=lambda a: "|".join(a) if isinstance(a, list) else str(a),
)
def test_base_python_env_no_conflict(env: str, base_python: list[str], ignore_conflict: bool) -> None:
    result = Python._validate_base_python(env, base_python, ignore_conflict)  # noqa: SLF001
    assert result is base_python


@pytest.mark.parametrize("ignore_conflict", [True, False])
@pytest.mark.parametrize(
    ("env", "base_python", "expected", "conflict"),
    [
        ("pypy", ["cpython"], "pypy", ["cpython"]),
        ("pypy2", ["pypy3"], "pypy2", ["pypy3"]),
        ("py3", ["py2"], "py3", ["py2"]),
        ("py38", ["py39"], "py38", ["py39"]),
        ("py38", ["py38", "py39"], "py38", ["py39"]),
        ("py38", ["python3"], "py38", ["python3"]),
        ("py310", ["py38", "py39"], "py310", ["py38", "py39"]),
        ("py3.11", ["py310"], "py3.11", ["py310"]),
        ("py310-magic", ["py39"], "py310", ["py39"]),
    ],
    ids=lambda a: "|".join(a) if isinstance(a, list) else str(a),
)
def test_base_python_env_conflict(
    env: str,
    base_python: list[str],
    expected: str,
    conflict: list[str],
    ignore_conflict: bool,
) -> None:
    if ignore_conflict:
        result = Python._validate_base_python(env, base_python, ignore_conflict)  # noqa: SLF001
        assert result == [expected]
    else:
        msg = f"env name {env} conflicting with base python {conflict[0]}"
        with pytest.raises(Fail, match=msg):
            Python._validate_base_python(env, base_python, ignore_conflict)  # noqa: SLF001


@pytest.mark.parametrize("ignore_conflict", [True, False, None])
def test_base_python_env_conflict_show_conf(tox_project: ToxProjectCreator, ignore_conflict: bool) -> None:
    py_ver = "".join(str(i) for i in sys.version_info[0:2])
    py_ver_next = "".join(str(i) for i in (sys.version_info[0], sys.version_info[1] + 2))
    ini = f"[testenv]\npackage=skip\nbase_python=py{py_ver_next}"
    if ignore_conflict is not None:
        ini += f"\n[tox]\nignore_base_python_conflict={ignore_conflict}"
    project = tox_project({"tox.ini": ini})
    result = project.run("c", "-e", f"py{py_ver}", "-k", "base_python")
    result.assert_success()
    if ignore_conflict:
        out = f"[testenv:py{py_ver}]\nbase_python = py{py_ver}\n"
    else:
        comma_in_exc = sys.version_info[0:2] <= (3, 6)
        out = (
            f"[testenv:py{py_ver}]\nbase_python = # Exception: Fail('env name py{py_ver} conflicting with"
            f" base python py{py_ver_next}'{',' if comma_in_exc else ''})\n"
        )
    result.assert_out_err(out, "")


def test_python_set_hash_seed(tox_project: ToxProjectCreator) -> None:
    ini = "[testenv]\npackage=skip\ncommands=python -c 'import os; print(os.environ[\"PYTHONHASHSEED\"])'"
    prj = tox_project({"tox.ini": ini})
    result = prj.run("r", "-e", "py", "--hashseed", "10")
    result.assert_success()
    assert result.out.splitlines()[1] == "10"


def test_python_generate_hash_seed(tox_project: ToxProjectCreator) -> None:
    ini = "[testenv]\npackage=skip\ncommands=python -c 'import os; print(os.environ[\"PYTHONHASHSEED\"])'"
    prj = tox_project({"tox.ini": ini})
    result = prj.run("r", "-e", "py")
    result.assert_success()
    assert 1 <= int(result.out.splitlines()[1]) <= (1024 if sys.platform == "win32" else 4294967295)


def test_python_keep_hash_seed(tox_project: ToxProjectCreator) -> None:
    ini = """
    [testenv]
    package=skip
    set_env=PYTHONHASHSEED=12
    commands=python -c 'import os; print(os.environ["PYTHONHASHSEED"])'
    """
    result = tox_project({"tox.ini": ini}).run("r", "-e", "py")
    result.assert_success()
    assert result.out.splitlines()[1] == "12"


def test_python_disable_hash_seed(tox_project: ToxProjectCreator) -> None:
    ini = "[testenv]\npackage=skip\ncommands=python -c 'import os; print(os.environ.get(\"PYTHONHASHSEED\"))'"
    prj = tox_project({"tox.ini": ini})
    result = prj.run("r", "-e", "py", "--hashseed", "notset")
    result.assert_success()
    assert result.out.splitlines()[1] == "None"


def test_python_set_hash_seed_negative(tox_project: ToxProjectCreator) -> None:
    result = tox_project({"tox.ini": ""}).run("r", "-e", "py", "--hashseed", "-1")
    result.assert_failed(2)
    assert "tox run: error: argument --hashseed: must be greater than zero" in result.err


def test_python_set_hash_seed_incorrect(tox_project: ToxProjectCreator) -> None:
    result = tox_project({"tox.ini": ""}).run("r", "-e", "py", "--hashseed", "ok")
    result.assert_failed(2)
    assert "tox run: error: argument --hashseed: invalid literal for int() with base 10: 'ok'" in result.err


def test_python_use_hash_seed_from_env(tox_project: ToxProjectCreator) -> None:
    ini = "[testenv]\npackage=skip"
    with patch.dict("os.environ", {"PYTHONHASHSEED": "13"}):
        result = tox_project({"tox.ini": ini}).run("c", "-e", "py", "-k", "setenv")
        result.assert_success()
        assert "PYTHONHASHSEED=13" in result.out


def test_python_hash_seed_from_env_random(tox_project: ToxProjectCreator) -> None:
    ini = "[testenv]\npackage=skip"
    with patch.dict("os.environ", {"PYTHONHASHSEED": "random"}):
        result = tox_project({"tox.ini": ini}).run("c", "-e", "py", "-k", "setenv")
        result.assert_success()
        assert "PYTHONHASHSEED=" in result.out


def test_python_hash_seed_from_env_and_override(tox_project: ToxProjectCreator) -> None:
    ini = "[testenv]\npackage=skip\ncommands=python -c 'import os; print(os.environ.get(\"PYTHONHASHSEED\"))'"
    with patch.dict("os.environ", {"PYTHONHASHSEED": "14"}):
        result = tox_project({"tox.ini": ini}).run("r", "-e", "py", "--hashseed", "15")
        result.assert_success()
        assert result.out.splitlines()[1] == "15"


def test_python_hash_seed_from_env_and_disable(tox_project: ToxProjectCreator) -> None:
    ini = "[testenv]\npackage=skip\ncommands=python -c 'import os; print(os.environ.get(\"PYTHONHASHSEED\"))'"
    with patch.dict("os.environ", {"PYTHONHASHSEED": "16"}):
        result = tox_project({"tox.ini": ini}).run("r", "-e", "py", "--hashseed", "notset")
        result.assert_success()
        assert result.out.splitlines()[1] == "None"


@pytest.mark.parametrize("in_ci", [True, False])
def test_list_installed_deps(in_ci: bool, tox_project: ToxProjectCreator, mocker: MockerFixture) -> None:
    mocker.patch("tox.config.cli.parser.is_ci", return_value=in_ci)
    result = tox_project({"tox.ini": "[testenv]\nskip_install = true"}).run("r", "-e", "py")
    if in_ci:
        assert "pip==" in result.out
    else:
        assert "pip==" not in result.out


@pytest.mark.parametrize("list_deps", ["--list-dependencies", "--no-list-dependencies"])
@pytest.mark.parametrize("in_ci", [True, False])
def test_list_installed_deps_explicit_cli(
    list_deps: str,
    in_ci: bool,
    tox_project: ToxProjectCreator,
    mocker: MockerFixture,
) -> None:
    mocker.patch("tox.config.cli.parser.is_ci", return_value=in_ci)
    result = tox_project({"tox.ini": "[testenv]\nskip_install = true"}).run(list_deps, "r", "-e", "py")
    if list_deps == "--list-dependencies":
        assert "pip==" in result.out
    else:
        assert "pip==" not in result.out


def test_usedevelop_with_nonexistent_basepython(tox_project: ToxProjectCreator) -> None:
    ini = "[testenv]\nusedevelop = true\n[testenv:unused]\nbasepython = /nonexistent/bin/python"
    project = tox_project({"tox.ini": ini})
    result = project.run()
    assert result.code == 0


@pytest.mark.parametrize(
    ("impl", "major", "minor", "arch"),
    [
        ("cpython", 3, 12, 64),
        ("pypy", 3, 9, 32),
    ],
)
def test_python_spec_for_sys_executable(impl: str, major: int, minor: int, arch: int, mocker: MockerFixture) -> None:
    version_info = SimpleNamespace(major=major, minor=minor, micro=5, releaselevel="final", serial=0)
    implementation = SimpleNamespace(
        name=impl,
        cache_tag=f"{impl}-{major}{minor}",
        version=version_info,
        hexversion=...,
        _multiarch=...,
    )
    mocker.patch.object(sys, "version_info", version_info)
    mocker.patch.object(sys, "implementation", implementation)
    mocker.patch.object(sys, "maxsize", 2**arch // 2 - 1)
    spec = Python._python_spec_for_sys_executable()  # noqa: SLF001
    assert spec.implementation == impl
    assert spec.major == major
    assert spec.minor == minor
    assert spec.architecture == arch
