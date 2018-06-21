import os
import subprocess
import textwrap

import pytest

from tox.config import parseconfig
from tox.session import Session


def test_make_sdist(initproj):
    initproj(
        "example123-0.5",
        filedefs={
            "tests": {"test_hello.py": "def test_hello(): pass"},
            "tox.ini": """
        """,
        },
    )
    config = parseconfig([])
    session = Session(config)
    sdist = session.get_installpkg_path()
    assert sdist.check()
    assert sdist.ext == ".zip"
    assert sdist == config.distdir.join(sdist.basename)
    sdist_2 = session.get_installpkg_path()
    assert sdist_2 == sdist
    sdist.write("hello")
    assert sdist.stat().size < 10
    sdist_new = Session(config).get_installpkg_path()
    assert sdist_new == sdist
    assert sdist_new.stat().size > 10


def test_make_sdist_distshare(tmpdir, initproj):
    distshare = tmpdir.join("distshare")
    initproj(
        "example123-0.6",
        filedefs={
            "tests": {"test_hello.py": "def test_hello(): pass"},
            "tox.ini": """
        [tox]
        distshare={}
        """.format(
                distshare
            ),
        },
    )
    config = parseconfig([])
    session = Session(config)
    sdist = session.get_installpkg_path()
    assert sdist.check()
    assert sdist.ext == ".zip"
    assert sdist == config.distdir.join(sdist.basename)
    sdist_share = config.distshare.join(sdist.basename)
    assert sdist_share.check()
    assert sdist_share.read("rb") == sdist.read("rb"), (sdist_share, sdist)


def test_sdist_latest(tmpdir, newconfig):
    distshare = tmpdir.join("distshare")
    config = newconfig(
        [],
        """
            [tox]
            distshare={}
            sdistsrc={{distshare}}/pkg123-*
    """.format(
            distshare
        ),
    )
    p = distshare.ensure("pkg123-1.4.5.zip")
    distshare.ensure("pkg123-1.4.5a1.zip")
    session = Session(config)
    sdist_path = session.get_installpkg_path()
    assert sdist_path == p


def test_installpkg(tmpdir, newconfig):
    p = tmpdir.ensure("pkg123-1.0.zip")
    config = newconfig(["--installpkg={}".format(p)], "")
    session = Session(config)
    sdist_path = session.get_installpkg_path()
    assert sdist_path == p


@pytest.mark.integration
@pytest.mark.pip
@pytest.mark.git
def test_pyproject_toml_with_setuptools_scm(initproj, cmd):
    initproj(
        "demo",
        filedefs={
            "demo": {
                "__init__.py": """
                from pkg_resources import get_distribution
                __version__ = get_distribution(__name__).version
                """
            },
            "setup.py": """
               from setuptools import setup, find_packages
               setup(
                   name='demo',
                   use_scm_version=True,
                   license='MIT',
                   platforms=['unix', 'win32'],
                   packages=find_packages('demo'),
                   package_dir={'':'demo'},
               )
               """,
            "setup.cfg": """
            [bdist_wheel]
            universal = 1
                        """,
            "pyproject.toml": """
            [build-system]
            requires = ["setuptools >= 35.0.2", "setuptools_scm >= 2.0.0, <3", "wheel >= 0.29.0"]
            """,
            "tox.ini": """
                [tox]
                build = wheel
                envlist = py

                [testenv]
                passenv = PYTHONPATH
                commands = python -c 'import demo; print(demo.__version__)'
            """,
        },
    )
    env = os.environ.copy()
    env["GIT_COMMITTER_NAME"] = "committer joe"
    env["GIT_AUTHOR_NAME"] = "author joe"
    env["EMAIL"] = "joe@bloomberg.com"
    subprocess.check_call(["git", "init"], env=env)
    subprocess.check_call(["git", "add", "."], env=env)
    subprocess.check_call(["git", "commit", "-m", "first commit"], env=env)
    subprocess.check_call(["git", "tag", "0.1"], env=env)

    result = cmd()
    expected = textwrap.dedent(
        """    GLOB wheel-make: {0}/setup.py
    py create: {0}/.tox/py
    py inst: {0}/.tox/dist/demo-0.1-py2.py3-none-any.whl
    py installed: demo==0.1
    py runtests: PYTHONHASHSEED='{1}'
    py runtests: commands[0] | python -c 'import demo; print(demo.__version__)'
    0.1
    ___________________________________ summary ____________________________________
      py: commands succeeded
      congratulations :)
    """.format(
            os.getcwd(), result.python_hash_seed
        )
    )
    assert result.out == expected
