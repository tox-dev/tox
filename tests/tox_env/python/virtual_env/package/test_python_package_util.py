from __future__ import annotations

import sys
from itertools import zip_longest
from typing import TYPE_CHECKING

import pytest
from packaging.requirements import Requirement
from pyproject_api import SubprocessFrontend

from tox.tox_env.errors import Fail
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
    for left, right in zip_longest(result, (Requirement("platformdirs>=4.3.8"), Requirement("colorama>=0.4.6"))):
        assert isinstance(right, Requirement)
        assert str(left) == str(right)


def test_load_dependency_many_extra(pkg_with_extras: PathDistribution) -> None:
    py_ver = ".".join(str(i) for i in sys.version_info[0:2])
    requires = pkg_with_extras.requires
    assert requires is not None
    result = dependencies_with_extras([Requirement(i) for i in requires], {"docs", "testing"}, "")
    sphinx = [Requirement("sphinx>=3"), Requirement("sphinx-rtd-theme<1,>=0.4.3")]
    exp = [
        Requirement("platformdirs>=4.3.8"),
        Requirement("colorama>=0.4.6"),
        *(sphinx if sys.version_info[0:2] <= (3, 8) else []),
        Requirement(f'covdefaults>=1.2; python_version == "2.7" or python_version == "{py_ver}"'),
        Requirement(f'pytest>=5.4.1; python_version == "{py_ver}"'),
        *(sphinx if sys.version_info[0:2] > (3, 8) else []),
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


def test_validate_extras_unknown() -> None:
    with pytest.raises(Fail, match=r"extras not found for package pkg: typo \(available: alpha, beta\)"):
        dependencies_with_extras([], {"typo"}, "pkg", available_extras={"alpha", "beta"})


def test_validate_extras_valid() -> None:
    requires = [Requirement('A; extra == "alpha"')]
    result = dependencies_with_extras(requires, {"alpha"}, "pkg", available_extras={"alpha", "beta"})
    assert [str(r) for r in result] == ["A"]


def test_validate_extras_none_skips_validation() -> None:
    result = dependencies_with_extras([], {"nonexistent"}, "pkg", available_extras=None)
    assert result == []


def test_validate_extras_empty_requested() -> None:
    result = dependencies_with_extras([], set(), "pkg", available_extras={"alpha"})
    assert result == []


def test_validate_extras_normalization() -> None:
    requires = [Requirement('A; extra == "my-extra"')]
    result = dependencies_with_extras(requires, {"my-extra"}, "pkg", available_extras={"my_extra"})
    assert [str(r) for r in result] == ["A"]


def test_validate_extras_no_available() -> None:
    with pytest.raises(Fail, match=r"extras not found for package pkg: alpha \(available: none\)"):
        dependencies_with_extras([], {"alpha"}, "pkg", available_extras=set())


def test_extras_underscore_hyphen_matching() -> None:
    """Extras with underscores in tox.ini should match hyphens in metadata markers (#3433)."""
    requires = [
        Requirement('dep-a; extra == "kebab-case"'),
        Requirement('dep-b; extra == "snake-case"'),
        Requirement('dep-c; extra == "kebab-case-2"'),
    ]
    result = dependencies_with_extras(requires, {"kebab-case", "snake_case", "kebab-case-2"}, "pkg")
    assert sorted(str(r) for r in result) == ["dep-a", "dep-b", "dep-c"]


def test_extras_underscore_in_markers() -> None:
    """Extras with underscores in markers should match hyphens in tox.ini (#3433)."""
    requires = [
        Requirement('dep-a; extra == "snake_case"'),
    ]
    result = dependencies_with_extras(requires, {"snake-case"}, "pkg")
    assert [str(r) for r in result] == ["dep-a"]


def test_extras_normalization_with_recursive() -> None:
    """Recursive extras with underscores should be resolved correctly (#3433)."""
    requires = [
        Requirement('dep1; extra == "my-extra"'),
        Requirement('name[sub_extra]; extra == "my-extra"'),
        Requirement('dep2; extra == "sub-extra"'),
    ]
    result = dependencies_with_extras(requires, {"my_extra"}, "name")
    assert sorted(str(r) for r in result) == ["dep1", "dep2"]
