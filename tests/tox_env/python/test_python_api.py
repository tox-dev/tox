from __future__ import annotations

import json
import os
import sys
import sysconfig
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Final

import pytest
from virtualenv.create.creator import Creator
from virtualenv.discovery.py_spec import PythonSpec
from virtualenv.run.session import Session

from tox.tox_env.python.api import Python
from tox.tox_env.python.virtual_env.api import VirtualEnv

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from tests.conftest import PatchPrevPy
    from tox.pytest import ToxProject, ToxProjectCreator, ToxRunOutcome


def test_requirements_txt(tox_project: ToxProjectCreator) -> None:
    prj = tox_project(
        {
            "tox.ini": "[testenv]\npackage=skip\ndeps=-rrequirements.txt",
            "requirements.txt": "nose",
        },
    )
    execute_calls = prj.patch_execute(lambda request: 0 if "install" in request.run_id else None)
    prj.run("r", "-e", "py").assert_success()

    assert execute_calls.call_count == 1
    got_cmd = execute_calls.call_args[0][3].cmd

    exp = ["python", "-I", "-m", "pip", "install", "-r", "requirements.txt"]
    assert got_cmd == exp


def test_conflicting_base_python_factor() -> None:
    major, minor = sys.version_info[0:2]
    name = f"py{major}{minor}-py{major}{minor - 1}"
    with pytest.raises(ValueError, match=f"conflicting factors py{major}{minor}, py{major}{minor - 1} in {name}"):
        Python.extract_base_python(name)


def test_conflicting_base_python_factor_explicit_version() -> None:
    with pytest.raises(ValueError, match=r"conflicting factors 3\.10, 3\.11 in 3\.10-3\.11"):
        Python.extract_base_python("3.10-3.11")


def test_conflicting_base_python_factor_mixed_style() -> None:
    with pytest.raises(ValueError, match=r"conflicting factors py310, 3\.11 in py310-3\.11"):
        Python.extract_base_python("py310-3.11")


def test_conflicting_base_python_factor_ignore(tox_project: ToxProjectCreator) -> None:
    ini = "[tox]\nenv_list=unit-py3.10-2.16\nignore_base_python_conflict=true\n[testenv]\npackage=skip\n"
    tox_project({"tox.ini": ini}).run("c", "-e", "unit-py3.10-2.16", "-k", "base_python").assert_success()


def test_conflicting_base_python_factor_no_ignore(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[tox]\nenv_list=unit-py3.10-2.16\n[testenv]\npackage=skip\n"})
    project.run("c", "-e", "unit-py3.10-2.16", "-k", "base_python", raise_on_config_fail=False).assert_failed(code=-1)


@pytest.mark.parametrize(
    ("files", "env"),
    [
        pytest.param(
            {"tox.ini": "[testenv:py311]\npackage=skip\nbase_python = {env:TOXPYTHON:python3.11}"},
            "py311",
            id="empty-environment-variable",
        ),
        pytest.param({"tox.ini": "[testenv:magic]\npackage=skip\nbase_python ="}, "magic", id="empty-ini"),
        pytest.param({"tox.toml": '[env.magic]\npackage = "skip"\nbase_python = ""'}, "magic", id="empty-toml"),
        pytest.param(
            {"tox.toml": '[env.magic]\npackage = "skip"\nbase_python = ["", " "]'},
            "magic",
            id="blank-toml-list",
        ),
    ],
)
def test_empty_base_python_fails(
    tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch, files: dict[str, str], env: str
) -> None:
    monkeypatch.setenv("TOXPYTHON", "")
    result: Final[ToxRunOutcome] = tox_project(files).run(
        "c", "-e", env, "-k", "base_python", raise_on_config_fail=False
    )
    result.assert_failed(code=-1)
    assert f"base_python for env {env} is empty" in result.out


def test_blank_base_python_entries_skipped(tox_project: ToxProjectCreator) -> None:
    result: Final[ToxRunOutcome] = tox_project({
        "tox.toml": '[env.magic]\npackage = "skip"\nbase_python = ["", "python3"]'
    }).run("c", "-e", "magic", "-k", "base_python")
    result.assert_success()
    assert "base_python = python3\n" in result.out


@pytest.mark.skipif(sys.platform == "win32", reason="mocks a POSIX venv layout (bin/python symlink)")
def test_build_wheel_in_non_base_pkg_env(
    tox_project: ToxProjectCreator,
    patch_prev_py: PatchPrevPy,
    demo_pkg_inline: Path,
    mocker: MockerFixture,
) -> None:
    def _fake_session(env_dir: list[str], **_: object) -> Session:
        bin_dir = Path(env_dir[0]) / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        (bin_dir / "python").symlink_to(sys.executable)
        return mocker.create_autospec(
            Session,
            instance=True,
            creator=mocker.create_autospec(Creator, instance=True, bin_dir=bin_dir, script_dir=bin_dir),
        )

    mocker.patch("tox.tox_env.python.virtual_env.api.session_via_cli", autospec=True, side_effect=_fake_session)
    prev_ver, impl, _ = patch_prev_py(True)
    prj = tox_project({"tox.ini": f"[tox]\nenv_list= {f'py{prev_ver}'}\n[testenv]\npackage=wheel"})
    execute_calls = prj.patch_execute(lambda request: 0 if "install" in request.run_id else None)
    prj.run("-r", "--root", str(demo_pkg_inline), "--workdir", str(prj.path / ".tox")).assert_success()
    calls = [(i[0][0].conf.name, i[0][3].run_id) for i in execute_calls.call_args_list]
    assert calls == [
        (f".pkg-{impl}{prev_ver}", "_optional_hooks"),
        (f".pkg-{impl}{prev_ver}", "get_requires_for_build_wheel"),
        (f".pkg-{impl}{prev_ver}", "build_wheel"),
        (f"py{prev_ver}", "install_package"),
        (f".pkg-{impl}{prev_ver}", "_exit"),
    ]


@pytest.mark.skipif(sys.platform == "win32", reason="mocks a POSIX venv layout (bin/python symlink)")
def test_build_wheel_in_free_threaded_pkg_env(
    tox_project: ToxProjectCreator,
    patch_prev_py: PatchPrevPy,
    demo_pkg_inline: Path,
    mocker: MockerFixture,
) -> None:
    def _fake_session(env_dir: list[str], **_: object) -> Session:
        bin_dir = Path(env_dir[0]) / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        (bin_dir / "python").symlink_to(sys.executable)
        return mocker.create_autospec(
            Session,
            instance=True,
            creator=mocker.create_autospec(Creator, instance=True, bin_dir=bin_dir, script_dir=bin_dir),
        )

    mocker.patch("tox.tox_env.python.virtual_env.api.session_via_cli", autospec=True, side_effect=_fake_session)
    prev_ver, impl, _ = patch_prev_py(True, free_threaded=True)
    prj = tox_project({"tox.ini": f"[tox]\nenv_list= {f'py{prev_ver}'}\n[testenv]\npackage=wheel"})
    execute_calls = prj.patch_execute(lambda request: 0 if "install" in request.run_id else None)
    prj.run("-r", "--root", str(demo_pkg_inline), "--workdir", str(prj.path / ".tox")).assert_success()
    calls = [(i[0][0].conf.name, i[0][3].run_id) for i in execute_calls.call_args_list]
    assert calls == [
        (f".pkg-{impl}{prev_ver}t", "_optional_hooks"),
        (f".pkg-{impl}{prev_ver}t", "get_requires_for_build_wheel"),
        (f".pkg-{impl}{prev_ver}t", "build_wheel"),
        (f"py{prev_ver}", "install_package"),
        (f".pkg-{impl}{prev_ver}t", "_exit"),
    ]


@pytest.mark.skipif(sys.platform == "win32", reason="mocks a POSIX venv layout (bin/python symlink)")
def test_build_wheel_in_debug_pkg_env(
    tox_project: ToxProjectCreator,
    patch_prev_py: PatchPrevPy,
    demo_pkg_inline: Path,
    mocker: MockerFixture,
) -> None:
    def _fake_session(env_dir: list[str], **_: object) -> Session:
        bin_dir = Path(env_dir[0]) / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        (bin_dir / "python").symlink_to(sys.executable)
        return mocker.create_autospec(
            Session,
            instance=True,
            creator=mocker.create_autospec(Creator, instance=True, bin_dir=bin_dir, script_dir=bin_dir),
        )

    mocker.patch("tox.tox_env.python.virtual_env.api.session_via_cli", autospec=True, side_effect=_fake_session)
    prev_ver, impl, _ = patch_prev_py(True, debug=True)
    prj = tox_project({"tox.ini": f"[tox]\nenv_list= {f'py{prev_ver}'}\n[testenv]\npackage=wheel"})
    execute_calls = prj.patch_execute(lambda request: 0 if "install" in request.run_id else None)
    prj.run("-r", "--root", str(demo_pkg_inline), "--workdir", str(prj.path / ".tox")).assert_success()
    calls = [(i[0][0].conf.name, i[0][3].run_id) for i in execute_calls.call_args_list]
    assert calls == [
        (f".pkg-{impl}{prev_ver}d", "_optional_hooks"),
        (f".pkg-{impl}{prev_ver}d", "get_requires_for_build_wheel"),
        (f".pkg-{impl}{prev_ver}d", "build_wheel"),
        (f"py{prev_ver}", "install_package"),
        (f".pkg-{impl}{prev_ver}d", "_exit"),
    ]


def test_diff_msg_added_removed_changed() -> None:
    before = {"A": "1", "F": "8", "C": "3", "D": "4", "E": "6"}
    after = {"G": "9", "B": "2", "C": "3", "D": "5", "E": "7"}
    expected = "python added A='1' | F='8', removed G='9' | B='2', changed D='5'->'4' | E='7'->'6'"
    assert Python._diff_msg(before, after) == expected  # ruff:ignore[private-member-access]  # cache diff ordering


def test_diff_msg_no_diff() -> None:
    assert Python._diff_msg({}, {}) == "python "  # ruff:ignore[private-member-access]  # empty cache diff


@pytest.mark.parametrize(
    ("env", "base_python"),
    [
        pytest.param("py3", "py3", id="py3-py3"),
        pytest.param("py3t", "py3t", id="py3t-py3t"),
        pytest.param("py311", "py311", id="py311-py311"),
        pytest.param("py311t", "py311t", id="py311t-py311t"),
        pytest.param("py3.12", "py3.12", id="py3-dot-12-py3-dot-12"),
        pytest.param("py3.12t", "py3.12t", id="py3-dot-12t-py3-dot-12t"),
        pytest.param("pypy2", "pypy2", id="pypy2-pypy2"),
        pytest.param("pypy2t", "pypy2t", id="pypy2t-pypy2t"),
        pytest.param("rustpython3", "rustpython3", id="rustpython3-rustpython3"),
        pytest.param("rustpython3t", "rustpython3t", id="rustpython3t-rustpython3t"),
        pytest.param("graalpy", "graalpy", id="graalpy-graalpy"),
        pytest.param("graalpyt", None, id="graalpyt-none"),
        pytest.param("jython", "jython", id="jython-jython"),
        pytest.param("jythont", None, id="jythont-none"),
        pytest.param("cpython3.8", "cpython3.8", id="cpython3-dot-8-cpython3-dot-8"),
        pytest.param("cpython3.8t", "cpython3.8t", id="cpython3-dot-8t-cpython3-dot-8t"),
        pytest.param("ironpython2.7", "ironpython2.7", id="ironpython2-dot-7-ironpython2-dot-7"),
        pytest.param("ironpython2.7t", "ironpython2.7t", id="ironpython2-dot-7t-ironpython2-dot-7t"),
        pytest.param("functional-py310", "py310", id="functional-dash-py310-py310"),
        pytest.param("functional-py310t", "py310t", id="functional-dash-py310t-py310t"),
        pytest.param("bar-pypy2-foo", "pypy2", id="bar-dash-pypy2-dash-foo-pypy2"),
        pytest.param("bar-foo2t-py2", "py2", id="bar-dash-foo2t-dash-py2-py2"),
        pytest.param("bar-pypy2t-foo", "pypy2t", id="bar-dash-pypy2t-dash-foo-pypy2t"),
        pytest.param("py", None, id="py-none"),
        pytest.param("pyt", None, id="pyt-none"),
        pytest.param("django-32", None, id="django-dash-32-none"),
        pytest.param("django-32t", None, id="django-dash-32t-none"),
        pytest.param("eslint-8.3", None, id="eslint-dash-8-dot-3-none"),
        pytest.param("eslint-8.3t", None, id="eslint-dash-8-dot-3t-none"),
        pytest.param("py-310", None, id="py-dash-310-none"),
        pytest.param("py-310t", None, id="py-dash-310t-none"),
        pytest.param("py3000", None, id="py3000-none"),
        pytest.param("py3000t", None, id="py3000t-none"),
        pytest.param("4.foo", None, id="4-dot-foo-none"),
        pytest.param("4.foot", None, id="4-dot-foot-none"),
        pytest.param("310", None, id="310-none"),
        pytest.param("310t", None, id="310t-none"),
        pytest.param("5", None, id="5-none"),
        pytest.param("5t", None, id="5t-none"),
        pytest.param("2000", None, id="2000-none"),
        pytest.param("2000t", None, id="2000t-none"),
        pytest.param("4000", None, id="4000-none"),
        pytest.param("4000t", None, id="4000t-none"),
        pytest.param("3.10", "3.10", id="3-dot-10-3-dot-10"),
        pytest.param("3.10t", "3.10t", id="3-dot-10t-3-dot-10t"),
        pytest.param("3.9", "3.9", id="3-dot-9-3-dot-9"),
        pytest.param("3.9t", "3.9t", id="3-dot-9t-3-dot-9t"),
        pytest.param("2.7", "2.7", id="2-dot-7-2-dot-7"),
        pytest.param("2.7t", "2.7t", id="2-dot-7t-2-dot-7t"),
        pytest.param("pypy-3.10", "pypy3.10", id="pypy-dash-3-dot-10-pypy3-dot-10"),
        pytest.param("pypy-3.10t", "pypy3.10t", id="pypy-dash-3-dot-10t-pypy3-dot-10t"),
        pytest.param("3.10-tests", "3.10", id="3-dot-10-dash-tests-3-dot-10"),
        pytest.param("3.10t-tests", "3.10t", id="3-dot-10t-dash-tests-3-dot-10t"),
        pytest.param("tests-3.10", "3.10", id="tests-dash-3-dot-10-3-dot-10"),
        pytest.param("tests-3.10t", "3.10t", id="tests-dash-3-dot-10t-3-dot-10t"),
        pytest.param("foo-3.14-bar", "3.14", id="foo-dash-3-dot-14-dash-bar-3-dot-14"),
        pytest.param("py311d", "py311d", id="py311d-py311d"),
        pytest.param("py311td", "py311td", id="py311td-py311td"),
        pytest.param("py3.12d", "py3.12d", id="py3-dot-12d-py3-dot-12d"),
        pytest.param("cpython3.8d", "cpython3.8d", id="cpython3-dot-8d-cpython3-dot-8d"),
        pytest.param("functional-py310d", "py310d", id="functional-dash-py310d-py310d"),
        pytest.param("bar-pypy2d-foo", "pypy2d", id="bar-dash-pypy2d-dash-foo-pypy2d"),
        pytest.param("3.10d", "3.10d", id="3-dot-10d-3-dot-10d"),
        pytest.param("3.10td", "3.10td", id="3-dot-10td-3-dot-10td"),
        pytest.param("pypy-3.10d", "pypy3.10d", id="pypy-dash-3-dot-10d-pypy3-dot-10d"),
        pytest.param("3.10d-tests", "3.10d", id="3-dot-10d-dash-tests-3-dot-10d"),
        pytest.param("pyd", None, id="pyd-none"),
        pytest.param("graalpyd", None, id="graalpyd-none"),
        pytest.param("django-32d", None, id="django-dash-32d-none"),
    ],
)
def test_extract_base_python(env: str, base_python: str | None) -> None:
    result = Python.extract_base_python(env)
    assert result == base_python


@pytest.mark.parametrize("ignore_conflict", [pytest.param(True, id="true"), pytest.param(False, id="false")])
@pytest.mark.parametrize(
    ("env", "base_python"),
    [
        pytest.param("magic", ["pypy"], id="magic-pypy"),
        pytest.param("magic", ["py39"], id="magic-py39"),
    ],
)
def test_base_python_env_no_conflict(
    tox_project: ToxProjectCreator, env: str, base_python: list[str], ignore_conflict: bool
) -> None:
    project = tox_project({
        "tox.toml": f"ignore_base_python_conflict = {str(ignore_conflict).lower()}\n"
        f'[env."{env}"]\npackage = "skip"\nbase_python = {json.dumps(base_python)}\n'
    })
    result = project.run("c", "-e", env, "-k", "base_python")
    result.assert_success()
    assert f"base_python = {base_python[0]}\n" in result.out


@pytest.mark.parametrize(
    ("env", "base_python", "expected"),
    [
        pytest.param("pypy", ["cpython"], "pypy", id="pypy-cpython-pypy"),
        pytest.param("pypy2", ["pypy3"], "pypy2", id="pypy2-pypy3-pypy2"),
        pytest.param("py3", ["py2"], "py3", id="py3-py2-py3"),
        pytest.param("py38", ["py39"], "py38", id="py38-py39-py38"),
        pytest.param("py38", ["py38", "py39"], "py38", id="py38-py38-py39-py38"),
        pytest.param("py38", ["python3"], "py38", id="py38-python3-py38"),
        pytest.param("py310", ["py38", "py39"], "py310", id="py310-py38-py39-py310"),
        pytest.param("py3.11", ["py310"], "py3.11", id="py3-dot-11-py310-py3-dot-11"),
        pytest.param("py310-magic", ["py39"], "py310", id="py310-dash-magic-py39-py310"),
    ],
)
def test_base_python_env_conflict_ignored(
    tox_project: ToxProjectCreator, env: str, base_python: list[str], expected: str
) -> None:
    project = tox_project({
        "tox.toml": f'ignore_base_python_conflict = true\n[env."{env}"]\n'
        f'package = "skip"\nbase_python = {json.dumps(base_python)}\n'
    })
    result = project.run("c", "-e", env, "-k", "base_python")
    result.assert_success()
    assert f"base_python = {expected}\n" in result.out


@pytest.mark.parametrize(
    ("env", "base_python", "conflict"),
    [
        pytest.param("pypy", ["cpython"], ["cpython"], id="pypy-cpython-cpython"),
        pytest.param("pypy2", ["pypy3"], ["pypy3"], id="pypy2-pypy3-pypy3"),
        pytest.param("py3", ["py2"], ["py2"], id="py3-py2-py2"),
        pytest.param("py38", ["py39"], ["py39"], id="py38-py39-py39"),
        pytest.param("py38", ["py38", "py39"], ["py39"], id="py38-py38-py39-py39"),
        pytest.param("py38", ["python3"], ["python3"], id="py38-python3-python3"),
        pytest.param("py310", ["py38", "py39"], ["py38", "py39"], id="py310-py38-py39-py38-py39"),
        pytest.param("py3.11", ["py310"], ["py310"], id="py3-dot-11-py310-py310"),
        pytest.param("py310-magic", ["py39"], ["py39"], id="py310-dash-magic-py39"),
    ],
)
def test_base_python_env_conflict_raises(
    tox_project: ToxProjectCreator, env: str, base_python: list[str], conflict: list[str]
) -> None:
    project = tox_project({"tox.toml": f'[env."{env}"]\npackage = "skip"\nbase_python = {json.dumps(base_python)}\n'})
    result = project.run("c", "-e", env, "-k", "base_python", raise_on_config_fail=False)
    result.assert_failed(code=-1)
    assert f"env name {env} conflicting with base python {conflict[0]}" in result.out


@pytest.mark.parametrize(
    ("env", "base_python", "ignore_conflict", "expected_code", "expected_output"),
    [
        pytest.param("pypy3", "PyPy3", False, 0, "base_python = PyPy3\n", id="major"),
        pytest.param("pypy39", "PYPY3.9", False, 0, "base_python = PYPY3.9\n", id="minor"),
        pytest.param("py39", "PyPy3.9", False, 0, "base_python = PyPy3.9\n", id="generic-implementation"),
        pytest.param("pypy39", "3.9", False, -1, "env name pypy39 conflicting with base python 3.9", id="missing"),
        pytest.param("pypy39", "3.9", True, 0, "base_python = pypy39\n", id="missing-override"),
    ],
)
def test_base_python_spec_implementation_case(
    tox_project: ToxProjectCreator,
    env: str,
    base_python: str,
    ignore_conflict: bool,
    expected_code: int,
    expected_output: str,
) -> None:
    project = tox_project({
        "tox.toml": f"""
        ignore_base_python_conflict = {str(ignore_conflict).lower()}
        [env."{env}"]
        package = "skip"
        base_python = "{base_python}"
        """,
    })
    result = project.run("c", "-e", env, "-k", "base_python", raise_on_config_fail=False)
    assert result.code == expected_code, result
    assert expected_output in result.out


@pytest.mark.parametrize(
    ("env", "implementation", "ignore_conflict", "expected_code", "expected_output"),
    [
        pytest.param("pypy3", "PyPy", False, 0, "base_python = {path}\n", id="major"),
        pytest.param("pypy39", "PyPy", False, 0, "base_python = {path}\n", id="minor"),
        pytest.param("pypy-3.9", "PyPy", False, 0, "base_python = {path}\n", id="explicit-version"),
        pytest.param("pypy39", "PYPY", False, 0, "base_python = {path}\n", id="uppercase"),
        pytest.param("pypy39", "pypy", False, 0, "base_python = {path}\n", id="lowercase"),
        pytest.param("py39", "PyPy", False, 0, "base_python = {path}\n", id="generic-implementation"),
        pytest.param("pypy39", "PyPy", True, 0, "base_python = {path}\n", id="matching-override"),
        pytest.param("pypy39", "CPython", False, -1, "base_python = # Exception: Fail({error})\n", id="conflict"),
        pytest.param("pypy310", "PyPy", False, -1, "base_python = # Exception: Fail({error})\n", id="version"),
        pytest.param("pypy39", "CPython", True, 0, "base_python = pypy39\n", id="conflict-override"),
        pytest.param("pypy310", "PyPy", True, 0, "base_python = pypy310\n", id="version-override"),
    ],
)
def test_base_python_path_implementation_case(
    tox_project: ToxProjectCreator,
    tmp_path: Path,
    mocker: MockerFixture,
    env: str,
    implementation: str,
    ignore_conflict: bool,
    expected_code: int,
    expected_output: str,
) -> None:
    path = tmp_path / "interpreter"
    mocker.patch.object(
        VirtualEnv,
        "python_spec_for_path",
        autospec=True,
        return_value=PythonSpec("discovered", implementation, 3, 9, None, 64, None, free_threaded=False),
    )
    project = tox_project({
        "tox.toml": f"""
        ignore_base_python_conflict = {str(ignore_conflict).lower()}
        [env."{env}"]
        package = "skip"
        base_python = '{path}'
        """,
    })

    result = project.run("c", "-e", env, "-k", "base_python", raise_on_config_fail=False)
    assert result.code == expected_code, result
    assert (
        expected_output.format(path=path, error=repr(f"env name {env} conflicting with base python {path}"))
        in result.out
    )


@pytest.mark.parametrize(
    "ignore_line",
    [
        pytest.param("", id="unset"),
        pytest.param("\n[tox]\nignore_base_python_conflict=False", id="false"),
    ],
)
def test_base_python_env_conflict_show_conf(tox_project: ToxProjectCreator, ignore_line: str) -> None:
    py_ver = "".join(str(i) for i in sys.version_info[0:2])
    py_ver_next = "".join(str(i) for i in (sys.version_info[0], sys.version_info[1] + 2))
    project = tox_project({"tox.ini": f"[testenv]\npackage=skip\nbase_python=py{py_ver_next}{ignore_line}"})
    result = project.run("c", "-e", f"py{py_ver}", "-k", "base_python", raise_on_config_fail=False)
    result.assert_failed(code=-1)
    out = (
        f"[testenv:py{py_ver}]\nbase_python = # Exception: Fail('env name py{py_ver} conflicting with"
        f" base python py{py_ver_next}')\n"
    )
    result.assert_out_err(out, "")


def test_base_python_env_conflict_ignored_show_conf(tox_project: ToxProjectCreator) -> None:
    py_ver = "".join(str(i) for i in sys.version_info[0:2])
    py_ver_next = "".join(str(i) for i in (sys.version_info[0], sys.version_info[1] + 2))
    project = tox_project({
        "tox.ini": f"[testenv]\npackage=skip\nbase_python=py{py_ver_next}\n[tox]\nignore_base_python_conflict=True"
    })
    result = project.run("c", "-e", f"py{py_ver}", "-k", "base_python", raise_on_config_fail=False)
    result.assert_success()
    result.assert_out_err(f"[testenv:py{py_ver}]\nbase_python = py{py_ver}\n", "")


def test_python_set_hash_seed(tox_project: ToxProjectCreator) -> None:
    ini = "[testenv]\npackage=skip\ncommands=python -c 'import os; print(os.environ[\"PYTHONHASHSEED\"])'"
    result = tox_project({"tox.ini": ini}).run("r", "-e", "py", "--hashseed", "10")
    result.assert_success()
    assert result.out.splitlines()[1] == "10"


@pytest.mark.parametrize(
    "host_env",
    [
        pytest.param({}, id="unset"),
        pytest.param({"PYTHONHASHSEED": ""}, id="empty"),
    ],
)
@pytest.mark.parametrize(
    "max_seed",
    [
        pytest.param(
            1024,
            id="windows",
            marks=pytest.mark.skipif(sys.platform != "win32", reason="windows seed limit"),
        ),
        pytest.param(
            4294967295,
            id="posix",
            marks=pytest.mark.skipif(sys.platform == "win32", reason="posix seed limit"),
        ),
    ],
)
def test_python_generate_hash_seed(
    tox_project: ToxProjectCreator,
    monkeypatch: pytest.MonkeyPatch,
    host_env: dict[str, str],
    max_seed: int,
) -> None:
    monkeypatch.delenv("PYTHONHASHSEED", raising=False)
    ini = "[testenv]\npackage=skip\ncommands=python -c 'import os; print(os.environ[\"PYTHONHASHSEED\"])'"
    monkeypatch.setattr(os, "environ", {**os.environ, **host_env})
    result = tox_project({"tox.ini": ini}).run("r", "-e", "py")
    result.assert_success()
    assert 1 <= int(result.out.splitlines()[1]) <= max_seed


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


def test_python_hash_seed_via_section_substitution(tox_project: ToxProjectCreator) -> None:
    ini = """
    [testenv]
    package=skip
    set_env=PYTHONHASHSEED=12
    [testenv:hs]
    commands=python -c 'import os; print(os.environ["PYTHONHASHSEED"])'
    set_env={[testenv]set_env}
    """
    result = tox_project({"tox.ini": ini}).run("r", "-e", "hs")
    result.assert_success()
    assert result.out.splitlines()[1] == "12"


def test_python_disable_hash_seed(tox_project: ToxProjectCreator) -> None:
    ini = "[testenv]\npackage=skip\ncommands=python -c 'import os; print(os.environ.get(\"PYTHONHASHSEED\"))'"
    result = tox_project({"tox.ini": ini}).run("r", "-e", "py", "--hashseed", "notset")
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


def test_python_use_hash_seed_from_env(tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch) -> None:
    ini = "[testenv]\npackage=skip"
    monkeypatch.setenv("PYTHONHASHSEED", "13")
    result = tox_project({"tox.ini": ini}).run("c", "-e", "py", "-k", "setenv")
    result.assert_success()
    assert "PYTHONHASHSEED=13" in result.out


def test_python_hash_seed_from_env_random(tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch) -> None:
    ini = "[testenv]\npackage=skip"
    monkeypatch.setenv("PYTHONHASHSEED", "random")
    result = tox_project({"tox.ini": ini}).run("c", "-e", "py", "-k", "setenv")
    result.assert_success()
    assert "PYTHONHASHSEED=" in result.out


def test_python_hash_seed_from_env_and_override(
    tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch
) -> None:
    ini = "[testenv]\npackage=skip\ncommands=python -c 'import os; print(os.environ.get(\"PYTHONHASHSEED\"))'"
    monkeypatch.setenv("PYTHONHASHSEED", "14")
    result = tox_project({"tox.ini": ini}).run("r", "-e", "py", "--hashseed", "15")
    result.assert_success()
    assert result.out.splitlines()[1] == "15"


def test_python_hash_seed_from_env_and_disable(tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch) -> None:
    ini = "[testenv]\npackage=skip\ncommands=python -c 'import os; print(os.environ.get(\"PYTHONHASHSEED\"))'"
    monkeypatch.setenv("PYTHONHASHSEED", "16")
    result = tox_project({"tox.ini": ini}).run("r", "-e", "py", "--hashseed", "notset")
    result.assert_success()
    assert result.out.splitlines()[1] == "None"


@pytest.mark.parametrize(
    ("in_ci", "pip_listed"),
    [pytest.param(True, True, id="true"), pytest.param(False, False, id="false")],
)
def test_list_installed_deps(
    in_ci: bool, pip_listed: bool, tox_project: ToxProjectCreator, mocker: MockerFixture
) -> None:
    mocker.patch("tox.config.cli.parser.is_ci", autospec=True, return_value=in_ci)
    result = tox_project({"tox.ini": "[testenv]\nskip_install = true"}).run("r", "-e", "py")
    assert ("pip==" in result.out) is pip_listed


@pytest.mark.parametrize(
    ("list_deps", "pip_listed"),
    [
        pytest.param("--list-dependencies", True, id="dash-dash-list-dash-dependencies"),
        pytest.param("--no-list-dependencies", False, id="dash-dash-no-dash-list-dash-dependencies"),
    ],
)
@pytest.mark.parametrize("in_ci", [pytest.param(True, id="true"), pytest.param(False, id="false")])
def test_list_installed_deps_explicit_cli(
    list_deps: str,
    pip_listed: bool,
    in_ci: bool,
    tox_project: ToxProjectCreator,
    mocker: MockerFixture,
) -> None:
    mocker.patch("tox.config.cli.parser.is_ci", autospec=True, return_value=in_ci)
    result = tox_project({"tox.ini": "[testenv]\nskip_install = true"}).run(list_deps, "r", "-e", "py")
    assert ("pip==" in result.out) is pip_listed


def test_usedevelop_with_nonexistent_basepython(tox_project: ToxProjectCreator) -> None:
    ini = "[testenv]\nusedevelop = true\n[testenv:unused]\nbasepython = /nonexistent/bin/python"
    result = tox_project({"tox.ini": ini}).run()
    assert result.code == 0


def test_default_base_python_used_when_no_factor(tox_project: ToxProjectCreator) -> None:
    py_ver = f"{sys.version_info[0]}.{sys.version_info[1]}"
    toml = f"""\
env_list = ["lint"]

[env_run_base]
package = "skip"
default_base_python = ["python{py_ver}"]
commands = [["python", "-c", "print('ok')"]]
"""
    result = tox_project({"tox.toml": toml}).run("c", "-e", "lint", "-k", "base_python")
    result.assert_success()
    assert f"python{py_ver}" in result.out


def test_default_base_python_ignored_when_factor_present(tox_project: ToxProjectCreator) -> None:
    py_ver = f"{sys.version_info[0]}{sys.version_info[1]}"
    toml = f"""\
env_list = ["py{py_ver}"]

[env_run_base]
package = "skip"
default_base_python = ["python3.8"]
commands = [["python", "-c", "print('ok')"]]
"""
    result = tox_project({"tox.toml": toml}).run("c", "-e", f"py{py_ver}", "-k", "base_python")
    result.assert_success()
    assert f"py{py_ver}" in result.out
    assert "python3.8" not in result.out


def test_default_base_python_ignored_when_base_python_explicit(tox_project: ToxProjectCreator) -> None:
    py_ver = f"{sys.version_info[0]}.{sys.version_info[1]}"
    toml = f"""\
env_list = ["lint"]

[env_run_base]
package = "skip"
default_base_python = ["python3.8"]
commands = [["python", "-c", "print('ok')"]]

[env.lint]
base_python = ["python{py_ver}"]
"""
    result = tox_project({"tox.toml": toml}).run("c", "-e", "lint", "-k", "base_python")
    result.assert_success()
    assert f"python{py_ver}" in result.out
    assert "python3.8" not in result.out


def test_base_python_string_in_toml(tox_project: ToxProjectCreator) -> None:
    py_ver = f"{sys.version_info[0]}.{sys.version_info[1]}"
    toml = f"""\
env_list = ["lint"]

[env_run_base]
package = "skip"
commands = [["python", "-c", "print('ok')"]]

[env.lint]
base_python = "python{py_ver}"
"""
    result = tox_project({"tox.toml": toml}).run("c", "-e", "lint", "-k", "base_python")
    result.assert_success()
    assert f"python{py_ver}" in result.out


def test_default_base_python_string_in_toml(tox_project: ToxProjectCreator) -> None:
    py_ver = f"{sys.version_info[0]}.{sys.version_info[1]}"
    toml = f"""\
env_list = ["lint"]

[env_run_base]
package = "skip"
default_base_python = "python{py_ver}"
commands = [["python", "-c", "print('ok')"]]
"""
    result = tox_project({"tox.toml": toml}).run("c", "-e", "lint", "-k", "base_python")
    result.assert_success()
    assert f"python{py_ver}" in result.out


@pytest.mark.parametrize(
    ("default_base_python", "expected"),
    [
        pytest.param("", sys.executable, id="unset"),
        pytest.param("default_base_python = []", "base_python = \n", id="empty-list"),
    ],
)
def test_base_python_when_default_unset_or_empty(
    tox_project: ToxProjectCreator, default_base_python: str, expected: str
) -> None:
    result: Final[ToxRunOutcome] = tox_project({
        "tox.toml": f"""\
env_list = ["lint"]

[env_run_base]
package = "skip"
{default_base_python}
commands = [["python", "-c", "print('ok')"]]
"""
    }).run("c", "-e", "lint", "-k", "base_python")
    result.assert_success()
    assert expected in result.out


@pytest.mark.parametrize(
    ("impl", "major", "minor", "arch", "free_threaded", "debug", "platform_str", "expected_machine", "expected_debug"),
    [
        pytest.param(
            "cpython",
            3,
            12,
            64,
            None,
            False,
            "linux-x86_64",
            "x86_64",
            None,
            id="cpython-3-12-64-none-false-linux-dash-x86-underscore-64-x86-underscore-64",
        ),
        pytest.param(
            "cpython",
            3,
            13,
            64,
            True,
            True,
            "linux-aarch64",
            "arm64",
            True,
            id="cpython-3-13-64-true-true-linux-dash-aarch64-arm64",
        ),
        pytest.param(
            "cpython",
            3,
            13,
            64,
            False,
            True,
            "win-amd64",
            "x86_64",
            True,
            id="cpython-3-13-64-false-true-win-dash-amd64-x86-underscore-64",
        ),
        pytest.param("pypy", 3, 9, 32, None, False, "win32", None, None, id="pypy-3-9-32-none-false-win32-none"),
        pytest.param(
            "cpython",
            3,
            12,
            64,
            None,
            False,
            "macosx-14.0-arm64",
            "arm64",
            None,
            id="cpython-3-12-64-none-false-macosx-dash-14-dot-0-dash-arm64-arm64",
        ),
    ],
)
def test_python_spec_for_sys_executable(
    impl: str,
    major: int,
    minor: int,
    arch: int,
    free_threaded: bool | None,
    debug: bool,
    platform_str: str,
    expected_machine: str,
    expected_debug: bool | None,
    mocker: MockerFixture,
) -> None:
    get_config_var_ = sysconfig.get_config_var

    def get_config_var(name: str) -> bool | int | str | None:
        if name == "Py_GIL_DISABLED":
            return free_threaded
        if name == "Py_DEBUG":
            return debug
        return get_config_var_(name)

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
    mocker.patch.object(sysconfig, "get_config_var", get_config_var)
    mocker.patch.object(sysconfig, "get_platform", autospec=True, return_value=platform_str)
    spec = Python._python_spec_for_sys_executable()  # ruff:ignore[private-member-access]  # simulated host ABI
    assert (spec.implementation, spec.major, spec.minor, spec.architecture, spec.free_threaded) == (
        impl,
        major,
        minor,
        arch,
        bool(free_threaded),
    )
    assert spec.debug is expected_debug
    assert spec.machine == expected_machine


@pytest.mark.parametrize(
    ("impl", "major", "minor", "arch", "free_threaded", "debug_build", "machine", "expected_debug"),
    [
        pytest.param(
            "cpython", 3, 13, 64, True, False, "x86_64", None, id="cpython-3-13-64-true-false-x86-underscore-64"
        ),
        pytest.param(
            "cpython", 3, 13, 64, False, True, "x86_64", True, id="cpython-3-13-64-false-true-x86-underscore-64"
        ),
        pytest.param(
            "cpython", 3, 13, 64, True, True, "x86_64", True, id="cpython-3-13-64-true-true-x86-underscore-64"
        ),
        pytest.param("cpython", 3, 12, 64, None, False, None, None, id="cpython-3-12-64-none-false-none"),
    ],
)
def test_python_spec_for_path(
    impl: str,
    major: int,
    minor: int,
    arch: int,
    free_threaded: bool | None,
    debug_build: bool,
    machine: str | None,
    expected_debug: bool | None,
    mocker: MockerFixture,
) -> None:
    info = SimpleNamespace(
        implementation=impl,
        version_info=SimpleNamespace(major=major, minor=minor, micro=5),
        architecture=arch,
        free_threaded=free_threaded,
        debug_build=debug_build,
        machine=machine,
    )
    mocker.patch.object(VirtualEnv, "get_virtualenv_py_info", autospec=True, return_value=info)
    spec = VirtualEnv.python_spec_for_path(Path("/does/not/matter"))
    assert (spec.implementation, spec.major, spec.minor, spec.architecture, spec.free_threaded) == (
        impl,
        major,
        minor,
        arch,
        bool(free_threaded),
    )
    assert spec.debug is expected_debug
    assert spec.machine == machine


@pytest.mark.parametrize(
    ("env", "spec"),
    [
        pytest.param("py313d", "cpython313d-64-x86_64", id="py313d-env-debug-base"),
        pytest.param("py313", "cpython313d-64-x86_64", id="py313-env-debug-base"),
    ],
)
def test_validate_base_python_debug_matches(
    tox_project: ToxProjectCreator, tmp_path: Path, env: str, spec: str, mocker: MockerFixture
) -> None:
    mocker.patch.object(
        VirtualEnv, "python_spec_for_path", autospec=True, return_value=PythonSpec.from_string_spec(spec)
    )
    base_python = tmp_path / "python3.13"
    project = tox_project({"tox.toml": f'[env."{env}"]\npackage = "skip"\nbase_python = "{base_python}"\n'})
    result = project.run("c", "-e", env, "-k", "base_python")
    result.assert_success()
    assert f"base_python = {base_python}\n" in result.out


def test_validate_base_python_debug_conflicts(
    tox_project: ToxProjectCreator, tmp_path: Path, mocker: MockerFixture
) -> None:
    mocker.patch.object(
        VirtualEnv,
        "python_spec_for_path",
        autospec=True,
        return_value=PythonSpec.from_string_spec("cpython313-64-x86_64"),
    )
    base_python = tmp_path / "python3.13"
    project = tox_project({"tox.toml": f'[env.py313d]\npackage = "skip"\nbase_python = "{base_python}"\n'})
    result = project.run("c", "-e", "py313d", "-k", "base_python", raise_on_config_fail=False)
    result.assert_failed(code=-1)
    assert "env name py313d conflicting with base python" in result.out


_PY_VER: Final[str] = f"{sys.version_info[0]}.{sys.version_info[1]}"
_PY_VER_NODOT: Final[str] = f"{sys.version_info[0]}{sys.version_info[1]}"


@pytest.mark.parametrize(
    ("config_file", "config", "version_content", "env", "expected"),
    [
        pytest.param(
            "tox.ini",
            "[testenv:mypy]\npackage=skip\nbase_python_file=.python-version\n",
            f"{_PY_VER}\n",
            "mypy",
            _PY_VER,
            id="ini",
        ),
        pytest.param(
            "tox.toml",
            'env_list = ["mypy"]\n\n[env.mypy]\npackage = "skip"\nbase_python_file = ".python-version"\n',
            f"{_PY_VER}\n",
            "mypy",
            _PY_VER,
            id="toml",
        ),
        pytest.param(
            "tox.ini",
            "[testenv:mypy]\npackage=skip\nbase_python_file=.python-version\n",
            f"# managed by tool\n\n{_PY_VER}\n",
            "mypy",
            _PY_VER,
            id="skips-comments",
        ),
        pytest.param(
            "tox.ini",
            "[testenv:mypy]\npackage=skip\nbase_python_file=.python-version\n",
            f"\ufeff{_PY_VER}\n",
            "mypy",
            _PY_VER,
            id="utf8-bom",
        ),
        pytest.param(
            "tox.ini",
            "[testenv]\npackage=skip\nbase_python_file=.python-version\n",
            "3.8\n",
            f"py{_PY_VER_NODOT}",
            f"py{_PY_VER_NODOT}",
            id="env-factor-wins",
        ),
    ],
)
def test_base_python_file(
    tox_project: ToxProjectCreator,
    config_file: str,
    config: str,
    version_content: str,
    env: str,
    expected: str,
) -> None:
    project = tox_project({config_file: config, ".python-version": version_content})
    result = project.run("c", "-e", env, "-k", "base_python")
    result.assert_success()
    assert f"base_python = {expected}\n" in result.out


_BASE_PYTHON_FILE_INI: Final[str] = "[testenv:mypy]\npackage=skip\nbase_python_file=.python-version\n"


@pytest.mark.parametrize(
    ("extra_files", "error_fragment"),
    [
        pytest.param({}, "no valid Python version found", id="not-found"),
        pytest.param({".python-version": "# just a comment\n"}, "no valid Python version found", id="empty"),
        pytest.param({".python-version": {"nested": "3.12"}}, "is not a regular file", id="directory"),
    ],
)
def test_base_python_file_error(
    tox_project: ToxProjectCreator, extra_files: dict[str, str | dict[str, str]], error_fragment: str
) -> None:
    project: Final[ToxProject] = tox_project({"tox.ini": _BASE_PYTHON_FILE_INI, **extra_files})
    result: Final[ToxRunOutcome] = project.run("c", "-e", "mypy", "-k", "base_python", raise_on_config_fail=False)
    result.assert_failed(code=-1)
    assert error_fragment in result.out


@pytest.mark.parametrize(
    "line",
    [
        pytest.param("a" * 8192, id="long-text"),
        pytest.param(f"{' ' * 8192}{_PY_VER}", id="long-whitespace-prefix"),
    ],
)
def test_base_python_file_long_line(tox_project: ToxProjectCreator, line: str) -> None:
    project = tox_project({"tox.ini": "[testenv:mypy]\npackage=skip\nbase_python_file=.python-version\n"})
    (project.path / ".python-version").write_text(line)
    result = project.run("c", "-e", "mypy", "-k", "base_python", raise_on_config_fail=False)
    result.assert_failed(code=-1)
    assert "exceeds 1024 characters" in result.out
    assert line[:1025] not in result.out


def test_base_python_file_not_utf8(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[testenv:mypy]\npackage=skip\nbase_python_file=.python-version\n"})
    (project.path / ".python-version").write_bytes(b"\xff\xfe\xfa\x80\n")
    result = project.run("c", "-e", "mypy", "-k", "base_python", raise_on_config_fail=False)
    result.assert_failed(code=-1)
    assert "base_python_file: cannot read '.python-version'" in result.out


@pytest.mark.parametrize(
    "ignored_line",
    [
        pytest.param(f"#{'x' * 8192}", id="long-comment"),
        pytest.param(f"{' ' * 8192}# comment", id="indented-long-comment"),
        pytest.param(" " * 8192, id="long-blank"),
    ],
)
def test_base_python_file_long_ignored_line(tox_project: ToxProjectCreator, ignored_line: str) -> None:
    project = tox_project({"tox.ini": "[testenv:mypy]\npackage=skip\nbase_python_file=.python-version\n"})
    (project.path / ".python-version").write_text(f"{ignored_line}\n{_PY_VER}\n")
    result = project.run("c", "-e", "mypy", "-k", "base_python")
    result.assert_success()
    assert f"base_python = {_PY_VER}\n" in result.out


@pytest.mark.parametrize(
    "content",
    [
        pytest.param("bin/python3\n", id="relative-path"),
        pytest.param("/usr/bin/python3\n", id="absolute-path"),
        pytest.param("evil\n", id="program-name"),
        pytest.param("system\n", id="no-version"),
        pytest.param("https://user:ghp_SECRET@github.com\n", id="secret-not-echoed"),
    ],
)
def test_base_python_file_rejects_non_version(tox_project: ToxProjectCreator, content: str) -> None:
    project: Final[ToxProject] = tox_project({"tox.ini": _BASE_PYTHON_FILE_INI, ".python-version": content})
    result: Final[ToxRunOutcome] = project.run("c", "-e", "mypy", "-k", "base_python", raise_on_config_fail=False)
    result.assert_failed(code=-1)
    assert "'.python-version' does not contain a Python version specifier" in result.out
    assert content.strip() not in result.out


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("3.12", id="major-minor"),
        pytest.param("3.12.1", id="micro"),
        pytest.param("python3", id="python-major"),
        pytest.param("py312", id="py-shorthand"),
        pytest.param("pypy3.10", id="pypy"),
        pytest.param("cpython3.13t", id="free-threaded"),
        pytest.param("3.14t", id="free-threaded-no-implementation"),
        pytest.param("PyPy3.10", id="case-insensitive-implementation"),
    ],
)
def test_base_python_file_accepts_version_spec(tox_project: ToxProjectCreator, value: str) -> None:
    project: Final[ToxProject] = tox_project({"tox.ini": _BASE_PYTHON_FILE_INI, ".python-version": f"{value}\n"})
    result: Final[ToxRunOutcome] = project.run("c", "-e", "mypy", "-k", "base_python")
    result.assert_success()
    assert f"base_python = {value}\n" in result.out


def test_base_python_file_conflict(tox_project: ToxProjectCreator) -> None:
    # Setting both base_python and base_python_file is an error.
    ini = f"[testenv:mypy]\npackage=skip\nbase_python=python{_PY_VER}\nbase_python_file=.python-version\n"
    project = tox_project({"tox.ini": ini, ".python-version": f"{_PY_VER}\n"})
    result = project.run("c", "-e", "mypy", "-k", "base_python", raise_on_config_fail=False)
    result.assert_failed(code=-1)
    assert "cannot set both base_python and base_python_file" in result.out


def test_base_python_file_global_testenv(tox_project: ToxProjectCreator) -> None:
    # base_python_file set in [testenv] applies to all non-factor envs.
    ini = f"[tox]\nenv_list=mypy,py{_PY_VER_NODOT}\n[testenv]\npackage=skip\nbase_python_file=.python-version\n"
    project = tox_project({"tox.ini": ini, ".python-version": f"{_PY_VER}\n"})
    result = project.run("c", "-e", "mypy", "-k", "base_python")
    result.assert_success()
    assert _PY_VER in result.out
    result = project.run("c", "-e", f"py{_PY_VER_NODOT}", "-k", "base_python")
    result.assert_success()
    assert f"py{_PY_VER_NODOT}" in result.out


def test_base_python_file_not_used_when_not_set(tox_project: ToxProjectCreator) -> None:
    toml = 'env_list = ["lint"]\n\n[env_run_base]\npackage = "skip"\ncommands = [["python", "-c", "print(1)"]]\n'
    result = tox_project({"tox.toml": toml}).run("c", "-e", "lint", "-k", "base_python")
    result.assert_success()
    assert sys.executable in result.out
