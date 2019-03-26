import os

from tox.config import parseconfig
from tox.package import get_package
from tox.session import Session


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
    package, dist = get_package(session)
    assert package.check()
    assert package.ext == ".zip"
    assert package == config.temp_dir.join("package", "1", package.basename)

    assert dist == config.distdir.join(package.basename)
    assert dist.check()
    assert os.stat(str(dist)).st_ino == os.stat(str(package)).st_ino

    sdist_share = config.distshare.join(package.basename)
    assert sdist_share.check()
    assert sdist_share.read("rb") == dist.read("rb"), (sdist_share, package)


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
    result = cmd("--sdistonly", "-e", "py")
    assert not result.ret
    dist_share_files = distshare.listdir()
    assert len(dist_share_files) == 1
    assert dist_share_files[0].check()

    result = cmd("-v", "--notest")
    result.assert_success()
    msg = "python inst: {}".format(result.session.package)
    assert msg in result.out, result.out
    operation = "copied" if not hasattr(os, "link") else "links"
    msg = "package {} {} to {}".format(
        os.sep.join(("pkg123", ".tox", ".tmp", "package", "1", "pkg123-0.7.zip")),
        operation,
        os.sep.join(("distshare", "pkg123-0.7.zip")),
    )
    assert msg in result.out, result.out
