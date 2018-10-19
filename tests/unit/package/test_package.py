import os

from tox.config import parseconfig
from tox.package import get_package
from tox.session import Session


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
            distshare
        ),
    )
    p = distshare.ensure("pkg123-1.4.5.zip")
    distshare.ensure("pkg123-1.4.5a1.zip")
    session = Session(config)
    _, dist = get_package(session)
    assert dist == p


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
    dist_share_files = distshare.listdir()
    assert len(dist_share_files) == 1
    assert dist_share_files[0].check()

    result = cmd("-v", "--notest")
    assert not result.ret, result.out
    msg = "python inst: {}".format(result.session.package.session_view)
    assert msg in result.out, result.out
    operation = "copied" if not hasattr(os, "link") else "links"
    msg = "package {} {} to {}".format(
        os.sep.join(("pkg123", ".tox", ".tmp", "package", "1", "pkg123-0.7.zip")),
        operation,
        os.sep.join(("distshare", "pkg123-0.7.zip")),
    )
    assert msg in result.out, result.out


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
    package = get_package(session)
    assert package.session_view.check()
    assert package.session_view.ext == ".zip"
    assert package.session_view == config.temp_dir.join(
        "package", "1", package.session_view.basename
    )

    assert package.dist == config.distdir.join(package.session_view.basename)
    assert package.dist.check()
    assert os.stat(str(package.dist)).st_ino == os.stat(str(package.session_view)).st_ino

    sdist_share = config.distshare.join(package.session_view.basename)
    assert sdist_share.check()
    assert sdist_share.read("rb") == package.dist.read("rb"), (sdist_share, package)
