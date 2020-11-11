import re
import sys

from tox.config import parseconfig
from tox.package import get_package
from tox.session import Session


def test_install_via_installpkg(mock_venv, initproj, cmd):
    base = initproj(
        "pkg-0.1",
        filedefs={
            "tox.ini": """
                [tox]
                install_cmd = python -m -c 'print("ok")' -- {opts} {packages}'
                """,
        },
    )
    fake_package = base.ensure(".tox", "dist", "pkg123-0.1.zip")
    result = cmd("-e", "py", "--notest", "--installpkg", str(fake_package.relto(base)))
    result.assert_success()


def test_installpkg(tmpdir, newconfig):
    p = tmpdir.ensure("pkg123-1.0.zip")
    config = newconfig(["--installpkg={}".format(p)], "")
    session = Session(config)
    _, sdist_path = get_package(session)
    assert sdist_path == p


def test_sdist_latest(tmpdir, newconfig):
    distshare = tmpdir.join("distshare")
    config = newconfig(
        [],
        """
            [tox]
            distshare={}
            sdistsrc={{distshare}}/pkg123-*
    """.format(
            distshare,
        ),
    )
    p = distshare.ensure("pkg123-1.4.5.zip")
    distshare.ensure("pkg123-1.4.5a1.zip")
    session = Session(config)
    _, dist = get_package(session)
    assert dist == p


def test_separate_sdist_no_sdistfile(cmd, initproj, tmpdir):
    distshare = tmpdir.join("distshare")
    initproj(
        ("pkg123-foo", "0.7"),
        filedefs={
            "tox.ini": """
            [tox]
            distshare={}
        """.format(
                distshare,
            ),
        },
    )
    result = cmd("--sdistonly", "-e", "py")
    assert not result.ret
    distshare_files = distshare.listdir()
    assert len(distshare_files) == 1
    sdistfile = distshare_files[0]
    assert "pkg123-foo-0.7.zip" in str(sdistfile)


def test_sdistonly(initproj, cmd):
    initproj(
        "example123",
        filedefs={
            "tox.ini": """
    """,
        },
    )
    result = cmd("-v", "--sdistonly", "-e", "py")
    assert not result.ret
    assert re.match(r".*sdist-make.*setup.py.*", result.out, re.DOTALL)
    assert "-mvirtualenv" not in result.out


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
    _, sdist = get_package(session)
    assert sdist.check()
    assert sdist.ext == ".zip"
    assert sdist == config.distdir.join(sdist.basename)
    _, sdist2 = get_package(session)
    assert sdist2 == sdist
    sdist.write("hello")
    assert sdist.stat().size < 10
    _, sdist_new = get_package(Session(config))
    assert sdist_new == sdist
    assert sdist_new.stat().size > 10


def test_build_backend_without_submodule(initproj, cmd):
    # The important part of this test is that the build backend
    # "inline_backend" is just a base package without a submodule.
    # (Regression test for #1344)
    initproj(
        "magic-0.1",
        filedefs={
            "tox.ini": """\
                [tox]
                isolated_build = true
                [testenv:.package]
                basepython = {}
                [testenv]
                setenv = PYTHONPATH = {{toxinidir}}
            """.format(
                sys.executable,
            ),
            "pyproject.toml": """\
                [build-system]
                requires = []
                build-backend = "inline_backend"
            """,
            # To trigger original bug, must be package with __init__.py
            "inline_backend": {
                "__init__.py": """\
                    import sys
                    def get_requires_for_build_sdist(*args, **kwargs):
                        return ["pathlib2;python_version<'3.4'"]

                    def build_sdist(sdist_directory, config_settings=None):
                        if sys.version_info[:2] >= (3, 4):
                            import pathlib
                        else:
                            import pathlib2 as pathlib

                        (pathlib.Path(sdist_directory) / "magic-0.1.0.tar.gz").touch()
                        return "magic-0.1.0.tar.gz"
                """,
            },
            ".gitignore": ".tox",
        },
        add_missing_setup_py=False,
    )
    result = cmd("--sdistonly", "-e", "py", "-v", "-v")
    result.assert_success(is_run_test_env=False)


def test_package_inject(initproj, cmd, monkeypatch, tmp_path):
    monkeypatch.delenv(str("PYTHONPATH"), raising=False)
    initproj(
        "example123-0.5",
        filedefs={
            "tox.ini": """
            [testenv:py]
            passenv = PYTHONPATH
            commands = python -c 'import os; assert os.path.exists(os.environ["TOX_PACKAGE"])'
        """,
        },
    )
    result = cmd("-q")
    assert result.session.getvenv("py").envconfig.setenv.get("TOX_PACKAGE")
