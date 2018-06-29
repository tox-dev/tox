import re

import pytest

from tox.exception import MissingDependency, MissingDirectory


def test__resolve_pkg_missing_directory(tmpdir, mocksession):
    distshare = tmpdir.join("distshare")
    spec = distshare.join("pkg123-*")
    with pytest.raises(MissingDirectory):
        mocksession._resolve_package(spec)


def test__resolve_pkg_missing_directory_in_distshare(tmpdir, mocksession):
    distshare = tmpdir.join("distshare")
    spec = distshare.join("pkg123-*")
    distshare.ensure(dir=1)
    with pytest.raises(MissingDependency):
        mocksession._resolve_package(spec)


def test__resolve_pkg_multiple_valid_versions(tmpdir, mocksession):
    distshare = tmpdir.join("distshare")
    distshare.ensure("pkg123-1.3.5.zip")
    p = distshare.ensure("pkg123-1.4.5.zip")
    result = mocksession._resolve_package(distshare.join("pkg123-*"))
    assert result == p
    mocksession.report.expect("info", "determin*pkg123*")


def test__resolve_pkg_with_invalid_version(tmpdir, mocksession):
    distshare = tmpdir.join("distshare")

    distshare.ensure("pkg123-1.something_bad.zip")
    distshare.ensure("pkg123-1.3.5.zip")
    p = distshare.ensure("pkg123-1.4.5.zip")

    result = mocksession._resolve_package(distshare.join("pkg123-*"))
    mocksession.report.expect("warning", "*1.something_bad*")
    assert result == p


def test__resolve_pkg_with_alpha_version(tmpdir, mocksession):
    distshare = tmpdir.join("distshare")
    distshare.ensure("pkg123-1.3.5.zip")
    distshare.ensure("pkg123-1.4.5a1.tar.gz")
    p = distshare.ensure("pkg123-1.4.5.zip")
    result = mocksession._resolve_package(distshare.join("pkg123-*"))
    assert result == p


def test__resolve_pkg_doubledash(tmpdir, mocksession):
    distshare = tmpdir.join("distshare")
    p = distshare.ensure("pkg-mine-1.3.0.zip")
    res = mocksession._resolve_package(distshare.join("pkg-mine*"))
    assert res == p
    distshare.ensure("pkg-mine-1.3.0a1.zip")
    res = mocksession._resolve_package(distshare.join("pkg-mine*"))
    assert res == p


def test_minversion(cmd, initproj):
    initproj(
        "interp123-0.5",
        filedefs={
            "tests": {"test_hello.py": "def test_hello(): pass"},
            "tox.ini": """
            [tox]
            minversion = 6.0
        """,
        },
    )
    result = cmd("-v")
    assert re.match(
        r"ERROR: MinVersionError: tox version is .*," r" required is at least 6.0", result.out
    )
    assert result.ret
