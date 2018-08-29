import re

from tox.config import parseconfig
from tox.package import get_package
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
    sdist = get_package(session)
    assert sdist.check()
    assert sdist.ext == ".zip"
    assert sdist == config.distdir.join(sdist.basename)
    sdist2 = get_package(session)
    assert sdist2 == sdist
    sdist.write("hello")
    assert sdist.stat().size < 10
    sdist_new = get_package(Session(config))
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
    sdist = get_package(session)
    assert sdist.check()
    assert sdist.ext == ".zip"
    assert sdist == config.distdir.join(sdist.basename)
    sdist_share = config.distshare.join(sdist.basename)
    assert sdist_share.check()
    assert sdist_share.read("rb") == sdist.read("rb"), (sdist_share, sdist)


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


def test_separate_sdist_no_sdistfile(cmd, initproj, tmpdir):
    distshare = tmpdir.join("distshare")
    initproj(
        ("pkg123-foo", "0.7"),
        filedefs={
            "tox.ini": """
            [tox]
            distshare={}
        """.format(
                distshare
            )
        },
    )
    result = cmd("--sdistonly")
    assert not result.ret
    distshare_files = distshare.listdir()
    assert len(distshare_files) == 1
    sdistfile = distshare_files[0]
    assert "pkg123-foo-0.7.zip" in str(sdistfile)


def test_separate_sdist(cmd, initproj, tmpdir):
    distshare = tmpdir.join("distshare")
    initproj(
        "pkg123-0.7",
        filedefs={
            "tox.ini": """
            [tox]
            distshare={}
            sdistsrc={{distshare}}/pkg123-0.7.zip
        """.format(
                distshare
            )
        },
    )
    result = cmd("--sdistonly")
    assert not result.ret
    sdistfiles = distshare.listdir()
    assert len(sdistfiles) == 1
    sdistfile = sdistfiles[0]
    result = cmd("-v", "--notest")
    assert not result.ret
    assert "python inst: {}".format(sdistfile) in result.out


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
    sdist_path = get_package(session)
    assert sdist_path == p


def test_installpkg(tmpdir, newconfig):
    p = tmpdir.ensure("pkg123-1.0.zip")
    config = newconfig(["--installpkg={}".format(p)], "")
    session = Session(config)
    sdist_path = get_package(session)
    assert sdist_path == p
