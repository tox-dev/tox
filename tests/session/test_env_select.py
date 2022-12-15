from __future__ import annotations

from tox.pytest import MonkeyPatch, ToxProjectCreator


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


def test_tox_skip_env(tox_project: ToxProjectCreator, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("TOX_SKIP_ENV", "m[y]py")
    project = tox_project({"tox.ini": "[tox]\nenv_list = py3{10,9},mypy"})
    outcome = project.run("l", "--no-desc", "-q")
    outcome.assert_success()
    outcome.assert_out_err("py310\npy39\n", "")


def test_tox_skip_env_cli(tox_project: ToxProjectCreator, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("TOX_SKIP_ENV", raising=False)
    project = tox_project({"tox.ini": "[tox]\nenv_list = py3{10,9},mypy"})
    outcome = project.run("l", "--no-desc", "-q", "--skip-env", "m[y]py")
    outcome.assert_success()
    outcome.assert_out_err("py310\npy39\n", "")


def test_tox_skip_env_logs(tox_project: ToxProjectCreator, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("TOX_SKIP_ENV", "m[y]py")
    project = tox_project({"tox.ini": "[tox]\nenv_list = py3{10,9},mypy"})
    outcome = project.run("l", "--no-desc")
    outcome.assert_success()
    outcome.assert_out_err("ROOT: skip environment mypy, matches filter 'm[y]py'\npy310\npy39\n", "")
