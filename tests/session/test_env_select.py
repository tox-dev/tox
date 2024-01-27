from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

from tox.config.cli.parse import get_options
from tox.session.env_select import _DYNAMIC_ENV_FACTORS, CliEnv, EnvSelector  # noqa: PLC2701
from tox.session.state import State

if TYPE_CHECKING:
    from tox.pytest import MonkeyPatch, ToxProjectCreator


CURRENT_PY_ENV = f"py{sys.version_info[0]}{sys.version_info[1]}"  # e.g. py310


@pytest.mark.parametrize(
    ("user_input", "env_names", "is_all", "is_default"),
    [
        (None, (), False, True),
        ("", (), False, True),
        ("a1", ("a1",), False, False),
        ("a1,b2,c3", ("a1", "b2", "c3"), False, False),
        (" a1, b2 ,  c3  ", ("a1", "b2", "c3"), False, False),
        #   If the user gives "ALL" as any envname, this becomes an "is_all" and other envnames are ignored.
        ("ALL", (), True, False),
        ("a1,ALL,b2", (), True, False),
        #   Zero-length envnames are ignored as being not present. This is not intentional.
        (",,a1,,,b2,,", ("a1", "b2"), False, False),
        (",,", (), False, True),
        #   Environment names with "invalid" characters are accepted here; the client is expected to deal with this.
        ("\x01.-@\x02,xxx", ("\x01.-@\x02", "xxx"), False, False),
    ],
)
def test_clienv(user_input: str, env_names: tuple[str], is_all: bool, is_default: bool) -> None:
    ce = CliEnv(user_input)
    assert (ce.is_all, ce.is_default_list, tuple(ce)) == (is_all, is_default, tuple(env_names))
    assert ce is not ce.is_default_list
    assert CliEnv(user_input) == ce


@pytest.mark.parametrize(
    ("user_input", "expected"),
    [
        ("", False),
        ("all", False),
        ("All", False),
        ("ALL", True),
        ("a,ALL,b", True),
    ],
)
def test_clienv_is_all(user_input: str, expected: bool) -> None:
    assert CliEnv(user_input).is_all is expected


def test_env_select_lazily_looks_at_envs() -> None:
    state = State(get_options(), [])
    env_selector = EnvSelector(state)
    # late-assigning env should be reflected in env_selector
    state.conf.options.env = CliEnv("py")
    assert set(env_selector.iter()) == {"py"}


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


@pytest.mark.parametrize(
    ("selection_arguments", "expect_envs"),
    [
        (
            ("-f", "cov", "django20"),
            ("py310-django20-cov", "py39-django20-cov"),
        ),
        (
            ("-f", "cov-django20"),
            ("py310-django20-cov", "py39-django20-cov"),
        ),
        (
            ("-f", "py39", "django20", "-f", "py310", "django21"),
            ("py310-django21-cov", "py310-django21", "py39-django20-cov", "py39-django20"),
        ),
    ],
)
def test_factor_select(
    tox_project: ToxProjectCreator,
    selection_arguments: tuple[str, ...],
    expect_envs: tuple[str, ...],
) -> None:
    ini = """
        [tox]
        env_list = py3{10,9}-{django20,django21}{-cov,}
        """
    project = tox_project({"tox.ini": ini})
    outcome = project.run("l", "--no-desc", *selection_arguments)
    outcome.assert_success()
    outcome.assert_out_err("{}\n".format("\n".join(expect_envs)), "")


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


def test_cli_env_can_be_specified_in_default(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": "[tox]\nenv_list=exists"})
    outcome = proj.run("r", "-e", "exists")
    outcome.assert_success()
    assert "exists" in outcome.out
    assert not outcome.err


def test_cli_env_can_be_specified_in_additional_environments(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": "[testenv:exists]"})
    outcome = proj.run("r", "-e", "exists")
    outcome.assert_success()
    assert "exists" in outcome.out
    assert not outcome.err


@pytest.mark.parametrize("env_name", ["py", CURRENT_PY_ENV, ".pkg"])
def test_allowed_implicit_cli_envs(env_name: str, tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": ""})
    outcome = proj.run("r", "-e", env_name)
    outcome.assert_success()
    assert env_name in outcome.out
    assert not outcome.err


@pytest.mark.parametrize("env_name", ["a", "b", "a-b", "b-a"])
def test_matches_hyphenated_env(env_name: str, tox_project: ToxProjectCreator) -> None:
    tox_ini = """
        [tox]
        env_list=a-b
        [testenv]
        package=skip
        commands_pre =
            a: python -c 'print("a")'
            b: python -c 'print("b")'
        commands=python -c 'print("ok")'
    """
    proj = tox_project({"tox.ini": tox_ini})
    outcome = proj.run("r", "-e", env_name)
    outcome.assert_success()
    assert env_name in outcome.out
    assert not outcome.err


_MINOR = sys.version_info.minor


@pytest.mark.parametrize(
    "env_name",
    [
        f"3.{_MINOR}",
        f"3.{_MINOR}-cov",
        "3-cov",
        "3",
        f"py3.{_MINOR}",
        f"py3{_MINOR}-cov",
        f"py3.{_MINOR}-cov",
    ],
)
def test_matches_combined_env(env_name: str, tox_project: ToxProjectCreator) -> None:
    tox_ini = """
        [testenv]
        package=skip
        commands =
            !cov: python -c 'print("without cov")'
            cov: python -c 'print("with cov")'
    """
    proj = tox_project({"tox.ini": tox_ini})
    outcome = proj.run("r", "-e", env_name)
    outcome.assert_success()
    assert env_name in outcome.out
    assert not outcome.err


@pytest.mark.parametrize(
    "env",
    [
        "py",
        "pypy",
        "pypy3",
        "pypy3.12",
        "pypy312",
        "py3",
        "py3.12",
        "py312",
        "3",
        "3.12",
        "3.12.0",
    ],
)
def test_dynamic_env_factors_match(env: str) -> None:
    assert _DYNAMIC_ENV_FACTORS.fullmatch(env)


@pytest.mark.parametrize(
    "env",
    [
        "cy3",
        "cov",
        "py10.1",
    ],
)
def test_dynamic_env_factors_not_match(env: str) -> None:
    assert not _DYNAMIC_ENV_FACTORS.fullmatch(env)


def test_suggest_env(tox_project: ToxProjectCreator) -> None:
    tox_ini = f"[testenv:release]\n[testenv:py3{_MINOR}]\n[testenv:alpha-py3{_MINOR}]\n"
    proj = tox_project({"tox.ini": tox_ini})
    outcome = proj.run("r", "-e", f"releas,p3{_MINOR},magic,alph-p{_MINOR}")
    outcome.assert_failed(code=-2)

    assert not outcome.err
    msg = (
        "ROOT: HandledError| provided environments not found in configuration file:\n"
        f"releas - did you mean release?\np3{_MINOR} - did you mean py3{_MINOR}?\nmagic\n"
        f"alph-p{_MINOR} - did you mean alpha-py3{_MINOR}?\n"
    )
    assert outcome.out == msg
