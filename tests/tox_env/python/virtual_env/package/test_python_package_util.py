from __future__ import annotations

import io
import re
import sys
import tarfile
from itertools import zip_longest
from typing import TYPE_CHECKING, Final

import pytest
from packaging.requirements import Requirement
from pyproject_api import SubprocessFrontend

from tox.tox_env.errors import Fail
from tox.tox_env.python.virtual_env.package.util import dependencies_with_extras, safe_extractall

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


@pytest.mark.parametrize(
    ("requires", "expected"),
    [
        pytest.param(
            [
                Requirement('six; extra == "dev"'),
                Requirement('name[dev]; python_version < "3.0" and extra == "all"'),
            ],
            ['six; python_version < "3.0"'],
            id="single",
        ),
        pytest.param(
            [
                Requirement('six; extra == "dev"'),
                Requirement('name[dev]; python_version < "3.0" and extra == "all"'),
                Requirement('name[all]; sys_platform == "win32" and extra == "dev"'),
            ],
            [
                'six; python_version < "3.0"',
                'six; python_version < "3.0" and sys_platform == "win32"',
            ],
            id="cycle",
        ),
    ],
)
def test_recursive_extra_keeps_marker_of_self_reference(requires: list[Requirement], expected: list[str]) -> None:
    assert [str(requirement) for requirement in dependencies_with_extras(requires, {"all"}, "name")] == expected


def test_recursive_extra_combines_markers_through_nested_self_references() -> None:
    requires: Final[list[Requirement]] = [
        Requirement('six; implementation_name == "cpython" and extra == "dev"'),
        Requirement('name[dev]; sys_platform == "win32" and extra == "mid"'),
        Requirement('name[mid]; python_version < "3.0" and extra == "all"'),
        Requirement('name[dev]; extra == "other"'),
    ]
    assert [str(requirement) for requirement in dependencies_with_extras(requires, {"all", "other"}, "name")] == [
        'six; implementation_name == "cpython"',
        'six; python_version < "3.0" and sys_platform == "win32" and implementation_name == "cpython"',
    ]


def test_loads_deps_recursive_extras_non_canonical_name() -> None:
    """A self-referential extra resolves even when the package name is not canonical."""
    requires = [
        Requirement('dep1; extra == "dev"'),
        Requirement('my-pkg[sub]; extra == "dev"'),
        Requirement('dep2; extra == "sub"'),
    ]
    result = dependencies_with_extras(requires, {"dev"}, "my_pkg")
    assert sorted(str(i) for i in result) == ["dep1", "dep2"]


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


@pytest.mark.usefixtures("extract_mode")
def test_safe_extractall_regular(tmp_path: Path) -> None:
    archive: Final[Path] = _make_tar(tmp_path / "ok.tar.gz", [("dir", "pkg-1.0", ""), ("file", "pkg-1.0/a.txt", "hi")])
    dest: Final[Path] = tmp_path / "dest"
    dest.mkdir()
    with tarfile.open(archive) as tar:
        safe_extractall(tar, dest)
    assert (dest / "pkg-1.0" / "a.txt").read_text() == "hi"


@pytest.fixture(
    params=[
        pytest.param(
            "data_filter",
            id="data-filter",
            marks=pytest.mark.skipif(not hasattr(tarfile, "data_filter"), reason="tarfile data filter unavailable"),
        ),
        pytest.param("fallback", id="fallback"),
    ],
)
def extract_mode(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    if request.param == "fallback":
        # Exercise the fallback even when tarfile provides its own filter.
        if hasattr(tarfile.TarFile, "extraction_filter"):
            monkeypatch.setattr(tarfile.TarFile, "extraction_filter", staticmethod(tarfile.fully_trusted_filter))
        monkeypatch.delattr(tarfile, "data_filter", raising=False)


def _make_tar(path: Path, members: list[tuple[str, str, str]]) -> Path:
    with tarfile.open(path, "w:gz") as tar:
        for kind, name, value in members:
            info: tarfile.TarInfo = tarfile.TarInfo(name)
            if kind == "dir":
                info.type = tarfile.DIRTYPE
                info.mode = 0o755
                tar.addfile(info)
            elif kind in {"sym", "hard"}:
                info.type = tarfile.SYMTYPE if kind == "sym" else tarfile.LNKTYPE
                info.linkname = value
                tar.addfile(info)
            else:
                data: bytes = value.encode()
                info.mode = 0o644
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
    return path


@pytest.mark.parametrize(
    ("members", "bad"),
    [
        pytest.param([("file", "../escape.txt", "evil")], "../escape.txt", id="traversal"),
        pytest.param(
            [("dir", "evil-1.0", ""), ("sym", "evil-1.0/escape", "{outside}"), ("file", "evil-1.0/escape/v.txt", "x")],
            "evil-1.0/escape",
            id="absolute-symlink",
        ),
        pytest.param(
            [
                ("dir", "evil-1.0", ""),
                ("sym", "evil-1.0/escape", "../../outside"),
                ("file", "evil-1.0/escape/v.txt", "x"),
            ],
            "evil-1.0/escape",
            id="relative-symlink",
        ),
        pytest.param([("hard", "evil-1.0/v.txt", "../outside/victim.txt")], "evil-1.0/v.txt", id="hardlink"),
    ],
)
@pytest.mark.usefixtures("extract_mode")
def test_safe_extractall_rejects_link_escape(
    tmp_path: Path,
    members: list[tuple[str, str, str]],
    bad: str,
) -> None:
    outside: Final[Path] = tmp_path / "outside"
    outside.mkdir()
    victim: Final[Path] = outside / "victim.txt"
    victim.write_text("original")
    archive: Final[Path] = _make_tar(
        tmp_path / "evil.tar.gz", [(kind, name, value.format(outside=outside)) for kind, name, value in members]
    )
    dest: Final[Path] = tmp_path / "dest"
    dest.mkdir()
    with tarfile.open(archive) as tar, pytest.raises(Fail, match=re.escape(f"cannot extract tar member {bad!r} into")):
        safe_extractall(tar, dest)
    assert (victim.read_text(), (outside / "v.txt").exists()) == ("original", False)


@pytest.mark.skipif(sys.platform == "win32", reason="needs symlink support")
@pytest.mark.parametrize("extract_mode", [pytest.param("fallback", id="fallback")], indirect=True)
@pytest.mark.usefixtures("extract_mode")
def test_safe_extractall_fallback_rejects_chained_symlink_escape(tmp_path: Path) -> None:
    # a/b/y -> ../.. stays inside, but a/b/x -> y/../.. only escapes once y is resolved on disk
    archive: Final[Path] = _make_tar(
        tmp_path / "evil.tar.gz",
        [("dir", "a", ""), ("dir", "a/b", ""), ("sym", "a/b/y", "../.."), ("sym", "a/b/x", "y/../..")],
    )
    dest: Final[Path] = tmp_path / "dest"
    dest.mkdir()
    with tarfile.open(archive) as tar, pytest.raises(Fail, match="cannot extract tar member 'a/b/x' into"):
        safe_extractall(tar, dest)
