"""Tests that require external access (e.g. pip install, virtualenv creation)"""
import os
import subprocess
import sys

import pytest

from tests.lib import need_git


@pytest.mark.network
def test_package_isolated_build_setuptools(initproj, cmd):
    initproj(
        "package_toml_setuptools-0.1",
        filedefs={
            "tox.ini": """
                    [tox]
                    isolated_build = true
                    [testenv:.package]
                    basepython = python
                """,
            "pyproject.toml": """
                    [build-system]
                    requires = ["setuptools >= 35.0.2", "setuptools_scm >= 2.0.0, <3"]
                    build-backend = 'setuptools.build_meta'
                    """,
        },
    )
    result = cmd("--sdistonly")
    assert result.ret == 0, result.out

    result2 = cmd("--sdistonly")
    assert result2.ret == 0, result.out
    assert ".package create" not in result2.out
    assert ".package recreate" not in result2.out


@pytest.mark.network
@need_git
@pytest.mark.skipif(sys.version_info < (3, 0), reason="flit is Python 3 only")
def test_package_isolated_build_flit(initproj, cmd):
    initproj(
        "package_toml_flit-0.1",
        filedefs={
            "tox.ini": """
                    [tox]
                    isolated_build = true
                    [testenv:.package]
                    basepython = python
                """,
            "pyproject.toml": """
                    [build-system]
                    requires = ["flit"]
                    build-backend = "flit.buildapi"

                    [tool.flit.metadata]
                    module = "package_toml_flit"
                    author = "Happy Harry"
                    author-email = "happy@harry.com"
                    home-page = "https://github.com/happy-harry/is"
                    """,
            ".gitignore": ".tox",
        },
        add_missing_setup_py=False,
    )
    env = os.environ.copy()
    env["GIT_COMMITTER_NAME"] = "committer joe"
    env["GIT_AUTHOR_NAME"] = "author joe"
    env["EMAIL"] = "joe@example.com"
    subprocess.check_call(["git", "init"], env=env)
    subprocess.check_call(["git", "add", "-A", "."], env=env)
    subprocess.check_call(["git", "commit", "-m", "first commit", "--no-gpg-sign"], env=env)
    result = cmd("--sdistonly")
    assert result.ret == 0, result.out

    result2 = cmd("--sdistonly")

    assert result2.ret == 0, result.out
    assert ".package create" not in result2.out
    assert ".package recreate" not in result2.out
