import pytest

from tox.pytest import ToxProject, ToxProjectCreator


@pytest.fixture()
def project(tox_project: ToxProjectCreator) -> ToxProject:
    ini = """
    [tox]
    env_list=py39,py38,py
    [testenv]
    description = with {basepython}
    deps = pypy:
    [testenv:py]
    basepython=py39,py38
    [testenv:fix]
    description = fix it
    """
    return tox_project({"tox.ini": ini})


def test_list_env(project: ToxProject) -> None:
    outcome = project.run("l")

    outcome.assert_success()
    expected = """
    default environments:
    py39 -> with py39
    py38 -> with py38
    py   -> with py39 py38

    additional environments:
    fix  -> fix it
    """
    outcome.assert_out_err(expected, "")


def test_list_env_default(project: ToxProject) -> None:
    outcome = project.run("l", "-d")

    outcome.assert_success()
    expected = """
    default environments:
    py39 -> with py39
    py38 -> with py38
    py   -> with py39 py38
    """
    outcome.assert_out_err(expected, "")


def test_list_env_quiet(project: ToxProject) -> None:
    outcome = project.run("l", "--no-desc")

    outcome.assert_success()
    expected = """
    py39
    py38
    py
    fix
    """
    outcome.assert_out_err(expected, "")


def test_list_env_quiet_default(project: ToxProject) -> None:
    outcome = project.run("l", "--no-desc", "-d")

    outcome.assert_success()
    expected = """
    py39
    py38
    py
    """
    outcome.assert_out_err(expected, "")
