import re

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
                """
        },
    )
    fake_package = base.ensure(".tox", "dist", "pkg123-0.1.zip")
    result = cmd("-e", "py", "--notest", "--installpkg", str(fake_package.relto(base)))
    assert result.ret == 0, result.out


def test_installpkg(tmpdir, newconfig):
    p = tmpdir.ensure("pkg123-1.0.zip")
    config = newconfig(["--installpkg={}".format(p)], "")
    session = Session(config)
    _, sdist_path = get_package(session)
    assert sdist_path == p


def test_sdistonly(initproj, cmd):
    initproj(
        "example123",
        filedefs={
            "tox.ini": """
    """
        },
    )
    result = cmd("-v", "--sdistonly")
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


def test_package_inject(initproj, cmd, monkeypatch, tmp_path):
    monkeypatch.delenv(str("PYTHONPATH"), raising=False)
    initproj(
        "example123-0.5",
        filedefs={
            "tox.ini": """
            [testenv:py]
            passenv = PYTHONPATH
            commands = python -c 'import os; assert os.path.exists(os.environ["TOX_PACKAGE"])'
        """
        },
    )
    result = cmd("-q")
    assert result.session.getvenv("py").envconfig.setenv.get("TOX_PACKAGE")
