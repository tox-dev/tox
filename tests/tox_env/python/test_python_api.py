from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

import pytest
from pytest_mock import MockerFixture

from tox.pytest import ToxProjectCreator
from tox.tox_env.errors import Fail
from tox.tox_env.python.api import Python


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
    name = f"py{major}{minor}-py{major}{minor-1}"
    with pytest.raises(ValueError, match=f"conflicting factors py{major}{minor}, py{major}{minor-1} in {name}"):
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
    assert Python._diff_msg(before, after) == expected


def test_diff_msg_no_diff() -> None:
    assert Python._diff_msg({}, {}) == "python "


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
    result = Python._validate_base_python(env, base_python, ignore_conflict)
    assert result is base_python


@pytest.mark.parametrize("ignore_conflict", [True, False])
@pytest.mark.parametrize(
    ("env", "base_python", "conflict"),
    [
        ("cpython", ["pypy"], ["pypy"]),
        ("pypy", ["cpython"], ["cpython"]),
        ("pypy2", ["pypy3"], ["pypy3"]),
        ("py3", ["py2"], ["py2"]),
        ("py38", ["py39"], ["py39"]),
        ("py38", ["py38", "py39"], ["py39"]),
        ("py38", ["python3"], ["python3"]),
        ("py310", ["py38", "py39"], ["py38", "py39"]),
        ("py3.11.1", ["py3.11.2"], ["py3.11.2"]),
        ("py3-64", ["py3-32"], ["py3-32"]),
        ("py310-magic", ["py39"], ["py39"]),
    ],
    ids=lambda a: "|".join(a) if isinstance(a, list) else str(a),
)
def test_base_python_env_conflict(env: str, base_python: list[str], conflict: list[str], ignore_conflict: bool) -> None:
    if ignore_conflict:
        result = Python._validate_base_python(env, base_python, ignore_conflict)
        assert result == [env]
    else:
        msg = f"env name {env} conflicting with base python {conflict[0]}"
        with pytest.raises(Fail, match=msg):
            Python._validate_base_python(env, base_python, ignore_conflict)


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


@pytest.mark.parametrize("in_ci", [True, False])
def test_list_installed_deps(in_ci: bool, tox_project: ToxProjectCreator, mocker: MockerFixture) -> None:
    mocker.patch("tox.tox_env.python.api.is_ci", return_value=in_ci)
    result = tox_project({"tox.ini": "[testenv]\nskip_install = true"}).run("r", "-e", "py")
    if in_ci:
        assert "pip==" in result.out
    else:
        assert "pip==" not in result.out
