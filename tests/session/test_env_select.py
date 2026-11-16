from __future__ import annotations

import os
import sys
from itertools import count
from textwrap import dedent
from typing import TYPE_CHECKING, Final

import pytest

from tox.config.cli.parse import get_options
from tox.session.env_select import CliEnv, EnvSelector
from tox.session.state import State
from tox.tox_env.python.virtual_env.package.pyproject import Pep517VenvPackager

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from tox.config.sets import EnvConfigSet
    from tox.pytest import MonkeyPatch, ToxProject, ToxProjectCreator, ToxRunOutcome


_CURRENT_PY_ENV: Final[str] = f"py{sys.version_info[0]}{sys.version_info[1]}"  # e.g. py310
_TWO_WHEEL_ENVS_INI: Final[str] = "[tox]\nenv_list = a,b\n[testenv]\npackage = wheel\n"


@pytest.mark.parametrize(
    ("user_input", "env_names", "is_all", "is_default"),
    [
        pytest.param(None, (), False, True, id="none--false-true"),
        pytest.param("", (), False, True, id="empty--false-true"),
        pytest.param("a1", ("a1",), False, False, id="a1-a1-false-false"),
        pytest.param("a1,b2,c3", ("a1", "b2", "c3"), False, False, id="a1-comma-b2-comma-c3-a1-b2-c3-false-false"),
        pytest.param(
            " a1, b2 ,  c3  ",
            ("a1", "b2", "c3"),
            False,
            False,
            id="space-a1-comma-space-b2-space-comma-space-space-c3-space-space-a1-b2-c3-false-false",
        ),
        #   If the user gives "ALL" as any envname, this becomes an "is_all" and other envnames are ignored.
        pytest.param("ALL", (), True, False, id="all--true-false"),
        pytest.param("a1,ALL,b2", (), True, False, id="a1-comma-all-comma-b2--true-false"),
        #   Zero-length envnames are ignored as being not present. This is not intentional.
        pytest.param(
            ",,a1,,,b2,,",
            ("a1", "b2"),
            False,
            False,
            id="comma-comma-a1-comma-comma-comma-b2-comma-comma-a1-b2-false-false",
        ),
        pytest.param(",,", (), False, True, id="comma-comma--false-true"),
        #   Environment names with "invalid" characters are accepted here; the client is expected to deal with this.
        pytest.param(
            "\x01.-@\x02,xxx",
            ("\x01.-@\x02", "xxx"),
            False,
            False,
            id="u1-dot-dash-at-u2-comma-xxx-u1-dot-dash-at-u2-xxx-false-false",
        ),
        #   Brace expansion produces the cartesian product of factors.
        pytest.param(
            "py{38,39}-pytest{6.x,7.x}",
            ("py38-pytest6.x", "py38-pytest7.x", "py39-pytest6.x", "py39-pytest7.x"),
            False,
            False,
            id="py-open-38-comma-39-close-dash-pytest-open-6-dot-x-comma-7-dot-x-close-py38-dash-pytest6-dot-x-py38-dash-pytest7-dot-x-py39-dash-pytest6-dot-x-py39-dash-pytest7-dot-x-false-false",
        ),
        pytest.param(
            "a{1,2},b", ("a1", "a2", "b"), False, False, id="a-open-1-comma-2-close-comma-b-a1-a2-b-false-false"
        ),
    ],
)
def test_clienv(user_input: str, env_names: tuple[str], is_all: bool, is_default: bool) -> None:
    ce = CliEnv(user_input)
    assert (ce.is_all, ce.is_default_list, tuple(ce)) == (is_all, is_default, tuple(env_names))
    assert CliEnv(user_input) == ce


@pytest.mark.parametrize(
    ("user_input", "expected"),
    [
        pytest.param("", False, id="empty-false"),
        pytest.param("all", False, id="all-false"),
        pytest.param("All", False, id="all-false-2"),
        pytest.param("ALL", True, id="all-true"),
        pytest.param("a,ALL,b", True, id="a-comma-all-comma-b-true"),
    ],
)
def test_clienv_is_all(user_input: str, expected: bool) -> None:
    assert CliEnv(user_input).is_all is expected


def test_clienv_iadd() -> None:
    cli_env = CliEnv("a,b")
    cli_env += CliEnv("c,d")
    assert list(cli_env) == ["a", "b", "c", "d"]


def test_clienv_iadd_from_default() -> None:
    cli_env = CliEnv()
    cli_env += CliEnv("c")
    assert list(cli_env) == ["c"]


def test_clienv_iadd_noop() -> None:
    cli_env = CliEnv("a")
    cli_env += CliEnv()
    assert list(cli_env) == ["a"]


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
    outcome = tox_project({"tox.ini": ini}).run("l", "--no-desc")
    outcome.assert_success()
    outcome.assert_out_err("py\npy310\npy39\nflake8\ntype\n", "")


def test_label_core_select(tox_project: ToxProjectCreator) -> None:
    ini = """
        [tox]
        labels =
            test = py3{10,9}
            static = flake8, type
        """
    outcome = tox_project({"tox.ini": ini}).run("l", "--no-desc", "-m", "test")
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
    outcome = tox_project({"tox.ini": ini}).run("l", "--no-desc", "-m", "test")
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
    outcome = tox_project({"tox.ini": ini}).run("l", "--no-desc", "-m", "test", "static")
    outcome.assert_success()
    outcome.assert_out_err("py310\npy39\nflake8\ntype\n", "")


@pytest.mark.parametrize(
    ("selection_arguments", "expect_envs"),
    [
        pytest.param(
            ("-f", "cov", "django20"),
            ("py310-django20-cov", "py39-django20-cov"),
            id="dash-f-cov-django20-py310-dash-django20-dash-cov-py39-dash-django20-dash-cov",
        ),
        pytest.param(
            ("-f", "cov-django20"),
            ("py310-django20-cov", "py39-django20-cov"),
            id="dash-f-cov-dash-django20-py310-dash-django20-dash-cov-py39-dash-django20-dash-cov",
        ),
        pytest.param(
            ("-f", "py39", "django20", "-f", "py310", "django21"),
            ("py310-django21-cov", "py310-django21", "py39-django20-cov", "py39-django20"),
            id="dash-f-py39-django20-dash-f-py310-django21-py310-dash-django21-dash-cov-py310-dash-django21-py39-dash-django20-dash-cov-py39-dash-django20",
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
    outcome = tox_project({"tox.ini": ini}).run("l", "--no-desc", *selection_arguments)
    outcome.assert_success()
    outcome.assert_out_err("{}\n".format("\n".join(expect_envs)), "")


@pytest.mark.parametrize(
    ("env_value", "expect_envs"),
    [
        pytest.param(
            "cov",
            ("py310-django20-cov", "py310-django21-cov", "py39-django20-cov", "py39-django21-cov"),
            id="cov-py310-dash-django20-dash-cov-py310-dash-django21-dash-cov-py39-dash-django20-dash-cov-py39-dash-django21-dash-cov",
        ),
        pytest.param(
            "py39,django20",
            ("py39-django20-cov", "py39-django20"),
            id="py39-comma-django20-py39-dash-django20-dash-cov-py39-dash-django20",
        ),
        pytest.param(
            "py39;py310",
            (
                "py310-django20-cov",
                "py310-django20",
                "py310-django21-cov",
                "py310-django21",
                "py39-django20-cov",
                "py39-django20",
                "py39-django21-cov",
                "py39-django21",
            ),
            id="py39-semicolon-py310-py310-dash-django20-dash-cov-py310-dash-django20-py310-dash-django21-dash-cov-py310-dash-django21-py39-dash-django20-dash-cov-py39-dash-django20-py39-dash-django21-dash-cov-py39-dash-django21",
        ),
    ],
)
def test_factor_select_via_env_var(
    tox_project: ToxProjectCreator,
    monkeypatch: MonkeyPatch,
    env_value: str,
    expect_envs: tuple[str, ...],
) -> None:
    monkeypatch.setenv("TOX_FACTORS", env_value)
    ini = """
        [tox]
        env_list = py3{10,9}-{django20,django21}{-cov,}
        """
    outcome = tox_project({"tox.ini": ini}).run("l", "--no-desc")
    outcome.assert_success()
    outcome.assert_out_err("{}\n".format("\n".join(expect_envs)), "")


@pytest.mark.parametrize(
    ("env_value", "expect_envs"),
    [
        pytest.param("old", ("py39",), id="old"),
        pytest.param("new", ("py310",), id="new"),
        pytest.param("old;new", ("py310", "py39"), id="both"),
        pytest.param("", ("py310", "py39"), id="empty"),
        pytest.param("unknown", (), id="unknown"),
    ],
)
def test_label_select_via_env_var(
    tox_project: ToxProjectCreator,
    monkeypatch: MonkeyPatch,
    env_value: str,
    expect_envs: tuple[str, ...],
) -> None:
    monkeypatch.setenv("TOX_LABELS", env_value)
    outcome: Final[ToxRunOutcome] = tox_project({
        "tox.ini": """
            [tox]
            env_list = py310, py39
            labels =
                old = py39
                new = py310
            """,
    }).run("l", "--no-desc")
    outcome.assert_success()
    outcome.assert_out_err("".join(f"{env}\n" for env in expect_envs), "")


def test_tox_skip_env(tox_project: ToxProjectCreator, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("TOX_SKIP_ENV", "m[y]py")
    outcome = tox_project({"tox.ini": "[tox]\nenv_list = py3{10,9},mypy"}).run("l", "--no-desc", "-q")
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
    outcome = tox_project({"tox.ini": "[tox]\nenv_list = py3{10,9},mypy"}).run("l", "--no-desc")
    outcome.assert_success()
    outcome.assert_out_err("ROOT: skip environment mypy, matches filter 'm[y]py'\npy310\npy39\n", "")


@pytest.mark.parametrize(
    "bad_filter", [pytest.param("[", id="lbracket"), pytest.param("(", id="lparen"), pytest.param("*", id="star")]
)
def test_tox_skip_env_invalid_regex(tox_project: ToxProjectCreator, monkeypatch: MonkeyPatch, bad_filter: str) -> None:
    monkeypatch.delenv("TOX_SKIP_ENV", raising=False)
    project = tox_project({"tox.ini": "[tox]\nenv_list = py3{10,9},mypy"})

    outcome = project.run("l", "--no-desc", "--skip-env", bad_filter)

    outcome.assert_failed()
    assert f"HandledError| invalid environment skip filter {bad_filter!r}" in outcome.out


def test_skip_env_cli_combines_with_e(tox_project: ToxProjectCreator, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("TOX_SKIP_ENV", raising=False)
    project = tox_project({"tox.ini": "[tox]\nenv_list = py3{10,9},mypy"})

    outcome = project.run("c", "--skip-env", "py39", "-e", "py310,py39", "-k", "env_name")

    outcome.assert_success()
    assert "[testenv:py310]" in outcome.out
    assert "[testenv:py39]" not in outcome.out


@pytest.mark.parametrize(
    ("selection_arguments", "skip_env", "expected"),
    [
        pytest.param(("-m", "test"), "py39", "py310\n", id="label"),
        pytest.param(("-f", "django20"), "py39-django20", "py310-django20\n", id="factor"),
    ],
)
def test_skip_env_cli_combines_with_group_selection(
    tox_project: ToxProjectCreator,
    monkeypatch: MonkeyPatch,
    selection_arguments: tuple[str, ...],
    skip_env: str,
    expected: str,
) -> None:
    monkeypatch.delenv("TOX_SKIP_ENV", raising=False)
    project = tox_project({
        "tox.ini": "[tox]\nenv_list = py310,py39,py310-django20,py39-django20\nlabels =\n    test = py310,py39",
    })

    outcome = project.run("l", "--no-desc", "-q", *selection_arguments, "--skip-env", skip_env)

    outcome.assert_success()
    outcome.assert_out_err(expected, "")


def test_skip_env_preserves_selection_exclusivity(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[tox]\nenv_list = py310,py39"})

    outcome = project.run("l", "--no-desc", "-m", "test", "-f", "py310", "--skip-env", "py39")

    outcome.assert_failed()
    assert "argument -f: not allowed with argument -m" in outcome.err


def test_multiple_e_flags_are_additive(tox_project: ToxProjectCreator) -> None:
    outcome = tox_project({"tox.ini": "[tox]\nenv_list=a,b,c"}).run("c", "-e", "a", "-e", "b", "-k", "env_name")
    outcome.assert_success()
    assert "[testenv:a]" in outcome.out
    assert "[testenv:b]" in outcome.out
    assert "[testenv:c]" not in outcome.out


def test_cli_env_can_be_specified_in_default(tox_project: ToxProjectCreator) -> None:
    outcome = tox_project({"tox.ini": "[tox]\nenv_list=exists"}).run("r", "-e", "exists")
    outcome.assert_success()
    assert "exists" in outcome.out
    assert not outcome.err


def test_cli_env_can_be_specified_in_additional_environments(tox_project: ToxProjectCreator) -> None:
    outcome = tox_project({"tox.ini": "[testenv:exists]"}).run("r", "-e", "exists")
    outcome.assert_success()
    assert "exists" in outcome.out
    assert not outcome.err


@pytest.mark.parametrize(
    "env_name",
    [
        pytest.param("py", id="py"),
        pytest.param(_CURRENT_PY_ENV, id="underscore-current-underscore-py-underscore-env"),
        pytest.param(".pkg", id="dot-pkg"),
    ],
)
def test_allowed_implicit_cli_envs(env_name: str, tox_project: ToxProjectCreator) -> None:
    outcome = tox_project({"tox.ini": ""}).run("r", "-e", env_name)
    outcome.assert_success()
    assert env_name in outcome.out
    assert not outcome.err


@pytest.mark.parametrize(
    "env_name",
    [
        pytest.param("a", id="a"),
        pytest.param("b", id="b"),
        pytest.param("a-b", id="a-dash-b"),
        pytest.param("b-a", id="b-dash-a"),
    ],
)
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
    outcome = tox_project({"tox.ini": tox_ini}).run("r", "-e", env_name)
    outcome.assert_success()
    assert env_name in outcome.out
    assert not outcome.err


_MINOR: Final[int] = sys.version_info.minor


@pytest.mark.parametrize(
    "env_name",
    [
        pytest.param(f"3.{_MINOR}", id="f-quote-3-dot-open-underscore-minor-close-quote"),
        pytest.param(f"3.{_MINOR}-cov", id="f-quote-3-dot-open-underscore-minor-close-dash-cov-quote"),
        pytest.param("3-cov", id="3-dash-cov"),
        pytest.param("3", id="3"),
        pytest.param(f"py3.{_MINOR}", id="f-quote-py3-dot-open-underscore-minor-close-quote"),
        pytest.param(f"py3{_MINOR}-cov", id="f-quote-py3-open-underscore-minor-close-dash-cov-quote"),
        pytest.param(f"py3.{_MINOR}-cov", id="f-quote-py3-dot-open-underscore-minor-close-dash-cov-quote"),
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
    outcome = tox_project({"tox.ini": tox_ini}).run("r", "-e", env_name)
    outcome.assert_success()
    assert env_name in outcome.out
    assert not outcome.err


@pytest.fixture
def lint_only_project(tox_project: ToxProjectCreator) -> ToxProject:
    toml = """
    env_list = ["lint"]
    [env_run_base]
    package = "skip"
    """
    return tox_project({"tox.toml": dedent(toml)})


@pytest.mark.parametrize(
    ("env_name", "base_python"),
    [
        pytest.param("cpython313", "cpython313", id="cpython"),
        pytest.param("cpython-3.13", "3.13", id="cpython-dash-version"),
        pytest.param("graalpy311", "graalpy311", id="graalpy"),
        pytest.param("jython2.7", "jython2.7", id="jython"),
        pytest.param("rustpython3", "rustpython3", id="rustpython"),
        pytest.param("ironpython3", "ironpython3", id="ironpython"),
        pytest.param("py313d", "py313d", id="debug-build"),
        pytest.param("py313td", "py313td", id="free-threaded-debug-build"),
    ],
)
def test_undeclared_interpreter_env_picks_base_python(
    lint_only_project: ToxProject, env_name: str, base_python: str
) -> None:
    outcome = lint_only_project.run("c", "-e", env_name, "-k", "base_python")

    outcome.assert_success()
    assert f"base_python = {base_python}\n" in outcome.out


def test_undeclared_cython_env_rejected(lint_only_project: ToxProject) -> None:
    outcome = lint_only_project.run("c", "-e", "cython313")

    outcome.assert_failed(code=-2)
    assert "provided environments not found in configuration file:\ncython313" in outcome.out


@pytest.mark.parametrize(
    "env_name",
    [pytest.param("functional-py312", id="functional-dash-py312"), pytest.param("functional", id="functional")],
)
def test_partial_section_match_rejected(env_name: str, tox_project: ToxProjectCreator) -> None:
    tox_ini = "[testenv]\nskip_install = true\ncommands=python -c 'print(1)'\n[testenv:functional{-py310}]\n"
    outcome = tox_project({"tox.ini": tox_ini}).run("r", "-e", env_name)
    outcome.assert_failed(code=-2)
    assert "provided environments not found in configuration file" in outcome.out


def test_factor_conditional_compound_accepted(tox_project: ToxProjectCreator) -> None:
    tox_ini = f"""
        [tox]
        env_list = py3{{{_MINOR},{_MINOR + 1}}}
        [testenv]
        package = skip
        commands =
            np: python -c 'print("np")'
            np-cov: python -c 'print("cov")'
    """
    outcome = tox_project({"tox.ini": tox_ini}).run("r", "-e", f"py3{_MINOR}-np-cov")
    outcome.assert_success()
    assert f"py3{_MINOR}-np-cov" in outcome.out


def test_suggest_env(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": f"[testenv:release]\n[testenv:py3{_MINOR}]\n[testenv:alpha-py3{_MINOR}]\n"})
    outcome = proj.run("r", "-e", f"releas,p3{_MINOR},magic,alph-p{_MINOR}")
    outcome.assert_failed(code=-2)

    assert not outcome.err
    msg = (
        "ROOT: HandledError| provided environments not found in configuration file:\n"
        f"releas - did you mean release?\np3{_MINOR} - did you mean py3{_MINOR}?\nmagic\n"
        f"alph-p{_MINOR} - did you mean alpha-py3{_MINOR}?\n"
    )
    assert outcome.out == msg


@pytest.mark.parametrize(
    "run_args",
    [
        pytest.param(["-e", "available"], id="only-available-requested"),
        pytest.param([], id="whole-env-list"),
    ],
)
def test_unavailable_runner_in_config_not_explicitly_requested(
    tox_project: ToxProjectCreator, run_args: list[str]
) -> None:
    # Unavailable runner in config should be marked NOT AVAILABLE if not explicitly requested.
    tox_toml = """
        [tool.tox]
        env_list = ["available", "unavailable"]

        [tool.tox.env_run_base]
        skip_install = true

        [tool.tox.env.available]
        commands = [["python", "-c", "print('available')"]]

        [tool.tox.env.unavailable]
        runner = "nonexistent-runner"
        commands = [["python", "-c", "print('unavailable')"]]
        """
    outcome = tox_project({"pyproject.toml": tox_toml}).run("r", *run_args)
    outcome.assert_success()
    assert "available: OK" in outcome.out
    assert "unavailable: NOT AVAILABLE" in outcome.out


def test_unavailable_runner_explicitly_requested(tox_project: ToxProjectCreator) -> None:
    # Explicitly requesting unavailable runner should fail with clear error.
    tox_toml = """
        [tool.tox.env_run_base]
        skip_install = true

        [tool.tox.env.unavailable]
        runner = "nonexistent-runner"
        commands = [["python", "-c", "print('unavailable')"]]
        """
    outcome = tox_project({"pyproject.toml": tox_toml}).run("r", "-e", "unavailable")
    outcome.assert_failed()
    assert "runner 'nonexistent-runner' for environment 'unavailable' is not available" in outcome.out


def test_multiple_unavailable_runners_implicit(tox_project: ToxProjectCreator) -> None:
    # Multiple unavailable runners should all be marked NOT AVAILABLE when not explicitly requested.
    tox_toml = """
        [tool.tox]
        env_list = ["available", "unavailable1", "unavailable2"]

        [tool.tox.env_run_base]
        skip_install = true

        [tool.tox.env.available]
        commands = [["python", "-c", "print('available')"]]

        [tool.tox.env.unavailable1]
        runner = "nonexistent-runner-1"
        commands = [["python", "-c", "print('unavailable1')"]]

        [tool.tox.env.unavailable2]
        runner = "nonexistent-runner-2"
        commands = [["python", "-c", "print('unavailable2')"]]
        """
    outcome = tox_project({"pyproject.toml": tox_toml}).run("r")
    outcome.assert_success()
    assert "available: OK" in outcome.out
    assert "unavailable1: NOT AVAILABLE" in outcome.out
    assert "unavailable2: NOT AVAILABLE" in outcome.out


@pytest.mark.parametrize(
    ("format_args", "expected"),
    [
        pytest.param([], "[testenv:available]\nenv_name = available\n", id="ini"),
        pytest.param(
            ["--format", "json"],
            '{\n  "env": {\n    "available": {\n      "env_name": "available"\n    }\n  }\n}\n',
            id="json",
        ),
        pytest.param(["--format", "toml"], '[env.available]\nenv_name = "available"\n', id="toml"),
    ],
)
def test_unavailable_runner_show_config(tox_project: ToxProjectCreator, format_args: list[str], expected: str) -> None:
    tox_toml: Final[str] = """
        [tool.tox]
        env_list = ["available", "unavailable"]

        [tool.tox.env_run_base]
        skip_install = true

        [tool.tox.env.unavailable]
        runner = "nonexistent-runner"
        """
    project: Final[ToxProject] = tox_project({"pyproject.toml": tox_toml})
    outcome: Final[ToxRunOutcome] = project.run("c", "-k", "env_name", *format_args)
    outcome.assert_success()
    assert "environment unavailable marked as unavailable" in outcome.out
    assert outcome.out.endswith(expected)


@pytest.mark.parametrize(
    ("env_list", "env_sections", "cli_env", "expected_suggestion"),
    [
        pytest.param(
            '["py310-lint", "py310-test", "py311-lint", "py311-test"]',
            ['[tool.tox.env."py310-lint"]', '[tool.tox.env."py311-lint"]'],
            "py3.10-lint",
            "py310-lint",
            id="dotted_py_version_with_factor",
        ),
        pytest.param(
            '["py310", "py311"]',
            ['[tool.tox.env."py310-cov"]', '[tool.tox.env."py311-cov"]'],
            "py3.10-cov",
            "py310-cov",
            id="dotted_py_version_single",
        ),
        pytest.param(
            '["310", "311"]',
            ['[tool.tox.env."310-lint"]', '[tool.tox.env."311-lint"]'],
            "3.10-lint",
            "310-lint",
            id="explicit_version_format",
        ),
    ],
)
def test_dotted_env_name_suggests_normalized(
    tox_project: ToxProjectCreator, env_list: str, env_sections: list[str], cli_env: str, expected_suggestion: str
) -> None:
    sections_text = "\n    ".join(f'{sec}\n    commands = [["echo", "specialized"]]' for sec in env_sections)
    toml = f"""
    [tool.tox]
    env_list = {env_list}

    [tool.tox.env_run_base]
    package = "skip"
    commands = [["echo", "testenv"]]

    {sections_text}
    """
    outcome = tox_project({"pyproject.toml": toml}).run("r", "-e", cli_env)
    outcome.assert_failed(code=-2)
    assert f"{cli_env} - did you mean {expected_suggestion}?" in outcome.out


def test_dotted_env_no_normalized_match_allows_adhoc(tox_project: ToxProjectCreator) -> None:
    toml = """
    [tool.tox]
    env_list = ["lint"]

    [tool.tox.env_run_base]
    package = "skip"
    commands = [["python", "-c", "print('adhoc')"]]
    """
    proj = tox_project({"pyproject.toml": toml})
    outcome = proj.run("r", "-e", f"py{sys.version_info[0]}.{sys.version_info[1]}-lint")
    outcome.assert_success()
    assert "adhoc" in outcome.out


def test_dotted_env_multiple_suggestions(tox_project: ToxProjectCreator) -> None:
    toml = """
    [tool.tox]
    env_list = ["py310-lint", "py311-cov"]

    [tool.tox.env_run_base]
    package = "skip"
    commands = [["echo", "testenv"]]

    [tool.tox.env."py310-lint"]
    commands = [["echo", "lint"]]

    [tool.tox.env."py311-cov"]
    commands = [["echo", "coverage"]]
    """
    outcome = tox_project({"pyproject.toml": toml}).run("r", "-e", "py3.10-lint,py3.11-cov")
    outcome.assert_failed(code=-2)
    assert "py3.10-lint - did you mean py310-lint?" in outcome.out
    assert "py3.11-cov - did you mean py311-cov?" in outcome.out


def test_pkg_env_creation_failure_is_not_masked(tox_project: ToxProjectCreator, mocker: MockerFixture) -> None:
    # A package env whose registration fails must surface its error, not a duplicate-config cascade (#3987).
    real_register_config = Pep517VenvPackager.register_config

    def failing_register_config(self: Pep517VenvPackager) -> None:
        real_register_config(self)
        msg = "no such device"
        raise OSError(msg)

    mocker.patch.object(Pep517VenvPackager, "register_config", failing_register_config)
    project = tox_project({
        "tox.ini": _TWO_WHEEL_ENVS_INI,
        "pyproject.toml": "",
    })

    with pytest.raises(OSError, match="no such device"):
        project.run("r", "--notest")


def test_pkg_env_creation_failure_reports_first_error(tox_project: ToxProjectCreator, mocker: MockerFixture) -> None:
    # When several environments fail to create, the first failure in definition order is the one reported.
    real_register_config = Pep517VenvPackager.register_config
    attempt = count(1)

    def failing_register_config(self: Pep517VenvPackager) -> None:
        real_register_config(self)
        msg = f"creation failure {next(attempt)}"
        raise OSError(msg)

    mocker.patch.object(Pep517VenvPackager, "register_config", failing_register_config)
    project = tox_project({
        "tox.ini": _TWO_WHEEL_ENVS_INI,
        "pyproject.toml": "",
    })

    with pytest.raises(OSError, match="creation failure 1"):
        project.run("r", "--notest")


def test_pkg_env_rollback_keeps_shared_env(tox_project: ToxProjectCreator) -> None:
    # One env's failed build must not destroy a package env other envs already use.
    ini = """
    [tox]
    skip_missing_interpreters = false
    [testenv]
    package = wheel
    [testenv:a]
    package = sdist
    [testenv:b]
    [testenv:c]
    wheel_build_env = b
    [testenv:.pkg]
    base_python = /nonexistent/python
    """

    outcome = tox_project({"tox.ini": ini, "pyproject.toml": ""}).run("c", "-e", "a,b,c", "-k", "env_name")

    outcome.assert_success()
    envs = outcome.state.envs
    assert envs["a"].package_env is envs[".pkg"]


def test_pkg_env_register_run_env_once(tox_project: ToxProjectCreator) -> None:
    # A run env whose wheel tag matches the package env must register with it exactly once.

    outcome = tox_project({"tox.ini": _TWO_WHEEL_ENVS_INI, "pyproject.toml": ""}).run("l")

    outcome.assert_success()
    pkg_env = outcome.state.envs[".pkg"]
    assert isinstance(pkg_env, Pep517VenvPackager)
    assert [conf.name for conf in pkg_env.builds["wheel"]] == ["a", "b"]


@pytest.mark.plugin_test
def test_pkg_env_skip_from_plugin_hook(tox_project: ToxProjectCreator) -> None:
    # A plugin raising Skip for a package env must mark the run env skipped, not crash.
    def plugin() -> None:  # pragma: no cover # the code is copied to a python file
        from tox.plugin import impl  # ruff:ignore[import-outside-top-level]  # deferred import
        from tox.tox_env.errors import Skip  # ruff:ignore[import-outside-top-level]  # deferred import

        @impl
        def tox_add_env_config(env_conf: EnvConfigSet) -> None:
            if env_conf.name == ".pkg":
                msg = "plugin opted out of packaging"
                raise Skip(msg)

    project = tox_project({
        "tox.ini": "[tox]\nenv_list = a\n[testenv]\npackage = wheel\n",
        "pyproject.toml": "",
        "toxfile.py": plugin,
    })

    project.run("l").assert_success()


@pytest.mark.parametrize(
    ("files", "expected_base", "expected_marker"),
    [
        pytest.param(
            {
                "tox.ini": dedent("""\
                    [testenv]
                    package = wheel
                    package_env = mypkg
                    set_env = MARKER=from_testenv
                    [testenv:mypkg]
                    package = skip
                    [pkgenv]
                    set_env = MARKER=from_pkgenv
                """),
                "pyproject.toml": "",
            },
            ["pkgenv"],
            "from_pkgenv",
            id="ini",
        ),
    ],
)
def test_pkg_env_redefined_uses_pkg_base(
    tox_project: ToxProjectCreator,
    files: dict[str, str],
    expected_base: list[str],
    expected_marker: str,
) -> None:
    # An env first built as a run env and then redefined as a package env must load the package base chain.

    outcome = tox_project(files).run("c", "-e", "mypkg,py", "-k", "set_env", "base")

    outcome.assert_success()
    pkg_conf = outcome.state.conf.get_env("mypkg")
    assert pkg_conf["base"] == expected_base
    assert pkg_conf["set_env"].load("MARKER") == expected_marker


def test_pkg_env_redefined_toml_uses_pkg_base(tox_project: ToxProjectCreator) -> None:
    # An env first built as a run env and then redefined as a package env must load the package base chain.
    files = {
        "tox.toml": dedent("""\
                    [env_run_base]
                    package = "wheel"
                    package_env = "mypkg"
                    set_env = { MARKER = "from_run_base" }
                    [env.mypkg]
                    package = "skip"
                    [env_pkg_base]
                    set_env = { MARKER = "from_pkg_base" }
                """),
        "pyproject.toml": "",
    }
    outcome = tox_project(files).run("c", "-e", "mypkg,py", "-k", "set_env", "base")
    outcome.assert_success()
    pkg_conf = outcome.state.conf.get_env("mypkg")
    assert pkg_conf["set_env"].load("MARKER") == "from_pkg_base"


@pytest.mark.parametrize(
    "files",
    [
        pytest.param(
            {
                "tox.ini": dedent("""\
                    [tox]
                    env_list = mypkg, py
                    [testenv]
                    package = wheel
                    package_env = mypkg
                    [testenv:mypkg]
                    package = skip
                """),
                "pyproject.toml": "",
            },
            id="ini",
        ),
        pytest.param(
            {
                "tox.toml": dedent("""\
                    env_list = ["mypkg", "py"]
                    [env_run_base]
                    package = "wheel"
                    package_env = "mypkg"
                    [env.mypkg]
                    package = "skip"
                """),
                "pyproject.toml": "",
            },
            id="toml",
        ),
    ],
)
def test_pkg_env_in_env_list_fails(tox_project: ToxProjectCreator, files: dict[str, str]) -> None:
    # An env cannot be asked to run and serve as a package environment; the conflict is reported, not hidden.

    outcome = tox_project(files).run("l")

    outcome.assert_failed()
    msg = "mypkg is listed in env_list but is used as a package environment by py; remove it from env_list or rename"
    assert msg in outcome.out, outcome.out


@pytest.mark.parametrize(
    ("files", "name"),
    [
        pytest.param({"tox.toml": 'env_list = ["{env:TOX_ENVS}"]'}, "/outside", id="absolute"),
        pytest.param({"tox.toml": 'env_list = ["{env:TOX_ENVS}"]'}, f"..{os.sep}outside", id="relative"),
        pytest.param({"tox.toml": 'env_list = ["{env:TOX_ENVS}"]'}, "", id="empty"),
        pytest.param({"tox.ini": "[tox]\nenv_list = {env:TOX_ENVS}"}, "..", id="parent"),
    ],
)
def test_env_name_rejects_path_component(
    tox_project: ToxProjectCreator, monkeypatch: MonkeyPatch, files: dict[str, str], name: str
) -> None:
    monkeypatch.setenv("TOX_ENVS", name)
    outcome: Final = tox_project(files).run("l")

    outcome.assert_failed()
    assert f"environment name {name!r} is not a valid single path component" in outcome.out


@pytest.mark.parametrize(
    ("files", "args"),
    [
        pytest.param({"tox.toml": 'labels = { ci = ["{env:TOX_ENVS}"] }'}, ("l", "-m", "ci"), id="label"),
        pytest.param({"tox.ini": "[testenv]\npackage = wheel\npackage_env = {env:TOX_ENVS}"}, ("l",), id="package"),
    ],
)
def test_env_name_rejects_path_in_derived_config(
    tox_project: ToxProjectCreator, monkeypatch: MonkeyPatch, files: dict[str, str], args: tuple[str, ...]
) -> None:
    monkeypatch.setenv("TOX_ENVS", "..")
    outcome: Final = tox_project(files).run(*args)

    outcome.assert_failed()
    assert "environment name '..' is not a valid single path component" in outcome.out


def test_env_name_rejects_path_in_cli_env(tox_project: ToxProjectCreator) -> None:
    outcome: Final = tox_project({"tox.toml": 'env_list = ["py"]'}).run("r", "-e", ".pkg_external/../outside")

    outcome.assert_failed()
    assert "environment name '.pkg_external/../outside' is not a valid single path component" in outcome.out
