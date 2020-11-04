from pathlib import Path

from packaging.requirements import Requirement

from tox.tox_env.python.api import Dep


def test_deps_path_eq() -> None:
    dep_1 = Dep(Path.cwd())
    dep_2 = Dep(Path.cwd())
    assert dep_1 == dep_2


def test_deps_path_ne() -> None:
    dep_1 = Dep(Path.cwd())
    dep_2 = Dep(Path.cwd() / "a")
    assert dep_1 != dep_2


def test_deps_req_eq() -> None:
    dep_1 = Dep(Requirement("pytest"))
    dep_2 = Dep(Requirement("pytest"))
    assert dep_1 == dep_2


def test_deps_req_ne() -> None:
    dep_1 = Dep(Requirement("pytest"))
    dep_2 = Dep(Requirement("tox"))
    assert dep_1 != dep_2
