import sys
from pathlib import Path
from typing import Callable, Tuple

import pytest
from packaging.requirements import Requirement
from pytest_mock import MockerFixture

from tox.pytest import MonkeyPatch, ToxProjectCreator
from tox.tox_env.python.api import Python, PythonDep


def test_deps_path_eq() -> None:
    dep_1 = PythonDep(Path.cwd())
    dep_2 = PythonDep(Path.cwd())
    assert dep_1 == dep_2


def test_deps_path_ne() -> None:
    dep_1 = PythonDep(Path.cwd())
    dep_2 = PythonDep(Path.cwd() / "a")
    assert dep_1 != dep_2


def test_deps_req_eq() -> None:
    dep_1 = PythonDep(Requirement("pytest"))
    dep_2 = PythonDep(Requirement("pytest"))
    assert dep_1 == dep_2


def test_deps_req_ne() -> None:
    dep_1 = PythonDep(Requirement("pytest"))
    dep_2 = PythonDep(Requirement("tox"))
    assert dep_1 != dep_2


def test_deps_repr() -> None:
    dep_1 = PythonDep(Path.cwd())
    assert repr(dep_1) == f"PythonDep(value={Path.cwd()!r})"


def test_requirements_txt(tox_project: ToxProjectCreator, monkeypatch: MonkeyPatch) -> None:
    prj = tox_project(
        {
            "tox.ini": "[testenv]\npackage=skip\ndeps=-rrequirements.txt",
            "requirements.txt": "nose",
        }
    )
    execute_calls = prj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = prj.run("r", "-e", "py")
    result.assert_success()
    tox_env = result.state.tox_env("py")

    assert execute_calls.call_count == 1
    exp = [str(tox_env.conf["env_python"]), "-I", "-m", "pip", "install", "-r"]
    got_cmd = execute_calls.call_args[0][3].cmd

    assert got_cmd[:-1] == exp

    req = Path(got_cmd[-1])
    assert req.parent == tox_env.core["tox_root"]
    assert req.name.startswith("requirements-")
    assert req.name.endswith(".txt")


def test_conflicting_base_python() -> None:
    major, minor = sys.version_info[0:2]
    name = f"py{major}{minor}-py{major}{minor-1}"
    with pytest.raises(ValueError, match=f"conflicting factors py{major}{minor}, py{major}{minor-1} in {name}"):
        Python.extract_base_python(name)


def test_build_wheel_in_non_base_pkg_env(
    tox_project: ToxProjectCreator,
    patch_prev_py: Callable[[bool], Tuple[str, str]],
    demo_pkg_inline: Path,
    mocker: MockerFixture,
) -> None:
    mocker.patch("tox.tox_env.python.virtual_env.api.session_via_cli")
    prev_ver, impl = patch_prev_py(True)
    prev_py = f"py{prev_ver}"
    pkg_env = f".pkg-{impl}{prev_ver}"
    prj = tox_project({"tox.ini": f"[tox]\nenv_list= {prev_py}\n[testenv]\npackage=wheel"})
    execute_calls = prj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = prj.run("-r", "--root", str(demo_pkg_inline))
    result.assert_success()
    calls = [(i[0][0].conf.name, i[0][3].run_id) for i in execute_calls.call_args_list]
    assert calls == [
        (".pkg", "get_requires_for_build_wheel"),
        (".pkg", "prepare_metadata_for_build_wheel"),
        (".pkg", "build_wheel"),
        (pkg_env, "get_requires_for_build_wheel"),
        (pkg_env, "build_wheel"),
        (pkg_env, "_exit"),
        (prev_py, "install_package"),
        (".pkg", "_exit"),
    ]
