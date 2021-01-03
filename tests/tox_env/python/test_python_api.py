from pathlib import Path

from packaging.requirements import Requirement

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
