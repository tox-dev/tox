from typing import Callable, Dict

import pytest

from tox.config.cli.parse import get_options
from tox.config.loader.api import Override
from tox.pytest import CaptureFixture, LogCaptureFixture, MonkeyPatch
from tox.session.common import CliEnv
from tox.session.state import State


def test_verbose(monkeypatch: MonkeyPatch) -> None:
    parsed, _, __, ___ = get_options("-v", "-v")
    assert parsed.verbosity == 4


def test_verbose_compound(monkeypatch: MonkeyPatch) -> None:
    parsed, _, __, ___ = get_options("-vv")
    assert parsed.verbosity == 4


def test_verbose_no_test(monkeypatch: MonkeyPatch) -> None:
    parsed, _, __, ___ = get_options("--notest", "-vv", "--runner", "virtualenv")
    assert vars(parsed) == {
        "verbose": 4,
        "quiet": 0,
        "colored": "no",
        "work_dir": None,
        "root_dir": None,
        "config_file": None,
        "result_json": None,
        "command": "legacy",
        "default_runner": "virtualenv",
        "force_dep": [],
        "sitepackages": False,
        "alwayscopy": False,
        "override": [],
        "show_config": False,
        "list_envs_all": False,
        "no_recreate_pkg": False,
        "list_envs": False,
        "devenv_path": None,
        "env": CliEnv(),
        "skip_missing_interpreters": "config",
        "skip_pkg_install": False,
        "recreate": False,
        "no_test": True,
        "package_only": False,
        "installpkg": None,
        "develop": False,
        "hashseed": "noset",
        "discover": [],
        "parallel": 0,
        "parallel_live": False,
        "parallel_no_spinner": False,
        "pre": False,
        "index_url": [],
    }


def test_env_var_exhaustive_parallel_values(
    monkeypatch: MonkeyPatch, core_handlers: Dict[str, Callable[[State], int]]
) -> None:
    monkeypatch.setenv("TOX_COMMAND", "run-parallel")
    monkeypatch.setenv("TOX_VERBOSE", "5")
    monkeypatch.setenv("TOX_QUIET", "1")
    monkeypatch.setenv("TOX_ENV", "py37,py36")
    monkeypatch.setenv("TOX_DEFAULT_RUNNER", "magic")
    monkeypatch.setenv("TOX_RECREATE", "yes")
    monkeypatch.setenv("TOX_NO_TEST", "yes")
    monkeypatch.setenv("TOX_PARALLEL", "3")
    monkeypatch.setenv("TOX_PARALLEL_LIVE", "no")
    monkeypatch.setenv("TOX_OVERRIDE", "a=b\nc=d")

    parsed, handlers, _, __ = get_options()
    assert vars(parsed) == {
        "alwayscopy": False,
        "colored": "no",
        "command": "legacy",
        "default_runner": "virtualenv",
        "develop": False,
        "devenv_path": None,
        "discover": [],
        "env": CliEnv(["py37", "py36"]),
        "force_dep": [],
        "hashseed": "noset",
        "index_url": [],
        "installpkg": None,
        "list_envs": False,
        "list_envs_all": False,
        "no_recreate_pkg": False,
        "no_test": True,
        "override": [Override("a=b"), Override("c=d")],
        "package_only": False,
        "parallel": 3,
        "parallel_live": False,
        "parallel_no_spinner": False,
        "pre": False,
        "quiet": 1,
        "recreate": True,
        "result_json": None,
        "show_config": False,
        "sitepackages": False,
        "skip_missing_interpreters": "config",
        "skip_pkg_install": False,
        "verbose": 5,
        "work_dir": None,
        "root_dir": None,
        "config_file": None,
    }
    assert parsed.verbosity == 4
    assert handlers == core_handlers


def test_ini_help(monkeypatch: MonkeyPatch, capsys: CaptureFixture) -> None:
    monkeypatch.setenv("TOX_VERBOSE", "5")
    monkeypatch.setenv("TOX_QUIET", "1")
    with pytest.raises(SystemExit) as context:
        get_options("-h")
    assert context.value.code == 0
    out, err = capsys.readouterr()
    assert not err
    assert "from env var TOX_VERBOSE" in out
    assert "from env var TOX_QUIET" in out


def test_bad_env_var(
    monkeypatch: MonkeyPatch, capsys: CaptureFixture, caplog: LogCaptureFixture, value_error: Callable[[str], str]
) -> None:
    monkeypatch.setenv("TOX_VERBOSE", "should-be-number")
    monkeypatch.setenv("TOX_QUIET", "1.00")
    parsed, _, __, ___ = get_options()
    assert parsed.verbose == 2
    assert parsed.quiet == 0
    assert parsed.verbosity == 2
    first = "env var TOX_VERBOSE='should-be-number' cannot be transformed to <class 'int'> because {}".format(
        value_error("invalid literal for int() with base 10: 'should-be-number'"),
    )
    second = "env var TOX_QUIET='1.00' cannot be transformed to <class 'int'> because {}".format(
        value_error("invalid literal for int() with base 10: '1.00'"),
    )
    capsys.readouterr()
    assert caplog.messages[0] == first
    assert caplog.messages[1] == second
    assert len(caplog.messages) == 2, caplog.text
