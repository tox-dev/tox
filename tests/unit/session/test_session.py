import re
import uuid

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


def test_tox_parallel_build_safe(initproj, cmd, mock_venv):
    initproj(
        "env_var_test",
        filedefs={
            "tox.ini": """
                          [tox]
                          envlist = py
                          [testenv]
                          skip_install = true
                          commands = python --version
                      """
        },
    )
    result = cmd("--parallel--safe-build")

    for path, base in (
        (result.session.config.distdir, "dist-"),
        (result.session.config.logdir, "log-"),
        (result.session.config.distshare, "distshare-"),
    ):
        basename = path.basename
        assert basename.startswith(base)
        assert uuid.UUID(basename[len(base) :], version=4)


def test_skip_sdist(cmd, initproj):
    initproj(
        "pkg123-0.7",
        filedefs={
            "tests": {"test_hello.py": "def test_hello(): pass"},
            "setup.py": """
            syntax error
        """,
            "tox.ini": """
            [tox]
            skipsdist=True
            [testenv]
            commands=python -c "print('done')"
        """,
        },
    )
    result = cmd()
    assert result.ret == 0


def test_skip_install_skip_package(cmd, initproj, mock_venv):
    initproj(
        "pkg123-0.7",
        filedefs={
            "setup.py": """raise RuntimeError""",
            "tox.ini": """
            [tox]
            envlist = py

            [testenv]
            skip_install = true
        """,
        },
    )
    result = cmd("--notest")
    assert result.ret == 0


@pytest.fixture()
def venv_filter_project(initproj, cmd):
    def func(*args):
        initproj(
            "pkg123-0.7",
            filedefs={
                "tox.ini": """
                    [tox]
                    envlist = {py27,py36}-{nocov,cov,diffcov}{,-extra}
                    skipsdist = true

                    [testenv]
                    skip_install = true
                    commands = python -c 'print("{envname}")'
                """
            },
        )
        result = cmd(*args)
        assert result.ret == 0
        active = [i.name for i in result.session.venvlist]
        return active, result

    yield func


def test_venv_filter_empty_all_active(venv_filter_project, monkeypatch):
    monkeypatch.delenv("TOX_SKIP_ENV", raising=False)
    active, result = venv_filter_project("-a")
    assert result.outlines == [
        "py27-nocov",
        "py27-nocov-extra",
        "py27-cov",
        "py27-cov-extra",
        "py27-diffcov",
        "py27-diffcov-extra",
        "py36-nocov",
        "py36-nocov-extra",
        "py36-cov",
        "py36-cov-extra",
        "py36-diffcov",
        "py36-diffcov-extra",
    ]
    assert active == result.outlines


def test_venv_filter_match_all_none_active(venv_filter_project, monkeypatch):
    monkeypatch.setenv("TOX_SKIP_ENV", ".*")
    active, result = venv_filter_project("-a")
    assert not active
    existing_envs = result.outlines

    _, result = venv_filter_project("-avv")
    for name in existing_envs:
        msg = "skip environment {}, matches filter '.*'".format(name)
        assert msg in result.outlines


def test_venv_filter_match_some_some_active(venv_filter_project, monkeypatch):
    monkeypatch.setenv("TOX_SKIP_ENV", "py27.*")
    active, result = venv_filter_project("-avvv")
    assert active == [
        "py36-nocov",
        "py36-nocov-extra",
        "py36-cov",
        "py36-cov-extra",
        "py36-diffcov",
        "py36-diffcov-extra",
    ]
