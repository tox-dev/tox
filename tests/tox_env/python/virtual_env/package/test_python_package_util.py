from __future__ import annotations

import sys
from itertools import zip_longest
from typing import TYPE_CHECKING

import pytest
from packaging.requirements import Requirement
from pyproject_api import SubprocessFrontend

from tox.tox_env.python.virtual_env.package.util import dependencies_with_extras

if TYPE_CHECKING:
    from pathlib import Path

from importlib.metadata import Distribution, PathDistribution


@pytest.fixture(scope="session")
def pkg_with_extras(pkg_with_extras_project: Path) -> PathDistribution:
    frontend = SubprocessFrontend(*SubprocessFrontend.create_args_from_folder(pkg_with_extras_project)[:-1])
    meta = pkg_with_extras_project / "meta"
    result = frontend.prepare_metadata_for_build_wheel(meta)
    assert result is not None
    return Distribution.at(result.metadata)


def test_load_dependency_no_extra(pkg_with_extras: PathDistribution) -> None:
    requires = pkg_with_extras.requires
    assert requires is not None
    result = dependencies_with_extras([Requirement(i) for i in requires], set(), "")
    for left, right in zip_longest(result, (Requirement("platformdirs>=2.1"), Requirement("colorama>=0.4.3"))):
        assert isinstance(right, Requirement)
        assert str(left) == str(right)


def test_load_dependency_many_extra(pkg_with_extras: PathDistribution) -> None:
    py_ver = ".".join(str(i) for i in sys.version_info[0:2])
    requires = pkg_with_extras.requires
    assert requires is not None
    result = dependencies_with_extras([Requirement(i) for i in requires], {"docs", "testing"}, "")
    exp = [
        Requirement("platformdirs>=2.1"),
        Requirement("colorama>=0.4.3"),
        Requirement("sphinx>=3"),
        Requirement("sphinx-rtd-theme<1,>=0.4.3"),
        Requirement(f'covdefaults>=1.2; python_version == "2.7" or python_version == "{py_ver}"'),
        Requirement(f'pytest>=5.4.1; python_version == "{py_ver}"'),
    ]
    for left, right in zip_longest(result, exp):
        assert isinstance(right, Requirement)
        assert str(left) == str(right)


def test_loads_deps_recursive_extras() -> None:
    requires = [
        Requirement("no-extra"),
        Requirement('dep1[magic]; extra=="dev"'),
        Requirement('dep1; extra=="test"'),
        Requirement('dep2[a,b]; extra=="test"'),
        Requirement('dep3; extra=="docs"'),
        Requirement('name; extra=="dev"'),
        Requirement('name[test]; extra=="dev"'),
    ]
    result = dependencies_with_extras(requires, {"dev"}, "name")
    assert [str(i) for i in result] == ["no-extra", "dep1[magic]", "dep1", "dep2[a,b]"]


def test_load_dependency_requirement_or_extras() -> None:
    requires = [Requirement('filelock<4.0.0,>=3.9.0; extra == "extras1" or extra == "extras2"')]
    for extras in ["extras1", "extras2"]:
        result = dependencies_with_extras(requires, {extras}, "")
        assert [str(r) for r in result] == ["filelock<4.0.0,>=3.9.0"]


@pytest.mark.parametrize("extra", ["extras1", "extras2", "extras3"])
def test_load_dependency_requirement_many_or_extras(extra: str) -> None:
    requires = [Requirement('filelock<4.0.0,>=3.9.0; extra == "extras1" or extra == "extras2" or extra == "extras3"')]
    result = dependencies_with_extras(requires, {extra}, "")
    assert [str(r) for r in result] == ["filelock<4.0.0,>=3.9.0"]
