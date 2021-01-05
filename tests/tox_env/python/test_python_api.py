from pathlib import Path

from packaging.requirements import Requirement
from pytest_mock import MockerFixture

from tox.pytest import MonkeyPatch, ToxProjectCreator
from tox.tox_env.python.api import PythonDep


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


def test_requirements_txt(tox_project: ToxProjectCreator, monkeypatch: MonkeyPatch, mocker: MockerFixture) -> None:
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
    exp = [
        str(tox_env.conf["env_python"]),
        "-I",
        "-m",
        "pip",
        "--disable-pip-version-check",
        "install",
        "-r",
    ]
    got_cmd = execute_calls.call_args[0][2].cmd

    assert got_cmd[:-1] == exp

    req = Path(got_cmd[-1])
    assert req.parent == tox_env.core["tox_root"]
    assert req.name.startswith("requirements-")
    assert req.name.endswith(".txt")
