from __future__ import annotations

from tox.pytest import ToxProjectCreator


def test_label_core_can_define(tox_project: ToxProjectCreator) -> None:
    ini = """
        [tox]
        labels =
            test = py3{10,9}
            static = flake8, type
        """
    project = tox_project({"tox.ini": ini})
    outcome = project.run("l", "--no-desc")
    outcome.assert_success()
    outcome.assert_out_err("py\npy310\npy39\nflake8\ntype\n", "")


def test_label_core_select(tox_project: ToxProjectCreator) -> None:
    ini = """
        [tox]
        labels =
            test = py3{10,9}
            static = flake8, type
        """
    project = tox_project({"tox.ini": ini})
    outcome = project.run("l", "--no-desc", "-m", "test")
    outcome.assert_success()
    outcome.assert_out_err("py310\npy39\n", "")


def test_label_select_trait(tox_project: ToxProjectCreator) -> None:
    ini = """
        [tox]
        env_list = py310, py39, flake8, type
        [testenv]
        labels = test
        [testenv:flake8]
        labels = static
        [testenv:type]
        labels = static
        """
    project = tox_project({"tox.ini": ini})
    outcome = project.run("l", "--no-desc", "-m", "test")
    outcome.assert_success()
    outcome.assert_out_err("py310\npy39\n", "")


def test_label_core_and_trait(tox_project: ToxProjectCreator) -> None:
    ini = """
        [tox]
        env_list = py310, py39, flake8, type
        labels =
            static = flake8, type
        [testenv]
        labels = test
        """
    project = tox_project({"tox.ini": ini})
    outcome = project.run("l", "--no-desc", "-m", "test", "static")
    outcome.assert_success()
    outcome.assert_out_err("py310\npy39\nflake8\ntype\n", "")


def test_factor_select(tox_project: ToxProjectCreator) -> None:
    ini = """
        [tox]
        env_list = py3{10,9}-{django20,django21}{-cov,}
        """
    project = tox_project({"tox.ini": ini})
    outcome = project.run("l", "--no-desc", "-f", "cov", "django20")
    outcome.assert_success()
    outcome.assert_out_err("py310-django20-cov\npy39-django20-cov\n", "")
