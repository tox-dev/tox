import sys

from tox.pytest import ToxProjectCreator


def test_platform_does_not_match(tox_project: ToxProjectCreator) -> None:
    ini = "[testenv]\npackage=skip\nplatform=wrong_platform"
    proj = tox_project({"tox.ini": ini})

    result = proj.run("r")
    result.assert_success()
    exp = "py: skipped environment because platform linux does not match wrong_platform"
    assert exp in result.out


def test_platform_matches(tox_project: ToxProjectCreator) -> None:
    ini = f"[testenv]\npackage=skip\nplatform={sys.platform}"
    proj = tox_project({"tox.ini": ini})
    result = proj.run("r")
    result.assert_success()
