import logging
import sys
import textwrap
from pathlib import Path
from typing import Any, Callable, Dict

import pytest
from pytest_mock import MockerFixture

from tox.config.cli.parse import get_options
from tox.config.loader.api import Override
from tox.pytest import CaptureFixture, LogCaptureFixture, MonkeyPatch
from tox.session.common import CliEnv
from tox.session.state import State


@pytest.fixture()
def exhaustive_ini(tmp_path: Path, monkeypatch: MonkeyPatch) -> Path:
    to = tmp_path / "tox.ini"
    to.write_text(
        textwrap.dedent(
            """
        [tox]
        colored = yes
        verbose = 5
        quiet = 1
        command = run-parallel
        env = py37, py36
        default_runner = virtualenv
        recreate = true
        no_test = true
        parallel = 3
        parallel_live = True
        override =
            a=b
            c=d
        """,
        ),
    )
    monkeypatch.setenv("TOX_CONFIG_FILE", str(to))
    return to


@pytest.mark.parametrize("content", ["[tox]", ""])
def test_ini_empty(
    tmp_path: Path,
    core_handlers: Dict[str, Callable[[State], int]],
    default_options: Dict[str, Any],
    mocker: MockerFixture,
    monkeypatch: MonkeyPatch,
    content: str,
) -> None:
    to = tmp_path / "tox.ini"
    monkeypatch.setenv("TOX_CONFIG_FILE", str(to))
    to.write_text(content)
    mocker.patch("tox.config.cli.parse.discover_source", return_value=mocker.MagicMock(path=Path()))
    parsed, handlers, _, __, ___ = get_options("r")
    assert vars(parsed) == default_options
    assert parsed.verbosity == 2
    assert handlers == core_handlers

    to.unlink()
    missing_parsed, ____, _, __, ___ = get_options("r")
    assert vars(missing_parsed) == vars(parsed)


@pytest.fixture()
def default_options(tmp_path: Path) -> Dict[str, Any]:
    return {
        "colored": "no",
        "command": "r",
        "default_runner": "virtualenv",
        "develop": False,
        "discover": [],
        "env": CliEnv(),
        "hash_seed": "noset",
        "install_pkg": None,
        "no_test": False,
        "override": [],
        "package_only": False,
        "quiet": 0,
        "recreate": False,
        "no_recreate_provision": False,
        "no_recreate_pkg": False,
        "result_json": None,
        "skip_missing_interpreters": "config",
        "skip_pkg_install": False,
        "verbose": 2,
        "work_dir": None,
        "root_dir": None,
        "config_file": (tmp_path / "tox.ini").absolute(),
    }


def test_ini_exhaustive_parallel_values(exhaustive_ini: Path, core_handlers: Dict[str, Callable[[State], int]]) -> None:
    parsed, handlers, _, __, ___ = get_options("p")
    assert vars(parsed) == {
        "colored": "yes",
        "command": "p",
        "default_runner": "virtualenv",
        "develop": False,
        "discover": [],
        "env": CliEnv(["py37", "py36"]),
        "hash_seed": "noset",
        "install_pkg": None,
        "no_test": True,
        "override": [Override("a=b"), Override("c=d")],
        "package_only": False,
        "no_recreate_pkg": False,
        "parallel": 3,
        "parallel_live": True,
        "parallel_no_spinner": False,
        "quiet": 1,
        "recreate": True,
        "no_recreate_provision": False,
        "result_json": None,
        "skip_missing_interpreters": "config",
        "skip_pkg_install": False,
        "verbose": 5,
        "work_dir": None,
        "root_dir": None,
        "config_file": exhaustive_ini,
    }
    assert parsed.verbosity == 4
    assert handlers == core_handlers


def test_ini_help(exhaustive_ini: Path, capsys: CaptureFixture) -> None:
    with pytest.raises(SystemExit) as context:
        get_options("-h")
    assert context.value.code == 0
    out, err = capsys.readouterr()
    assert not err
    assert f"config file '{exhaustive_ini}' active (changed via env var TOX_CONFIG_FILE)"


def test_bad_cli_ini(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    caplog: LogCaptureFixture,
    default_options: Dict[str, Any],
    mocker: MockerFixture,
) -> None:
    mocker.patch("tox.config.cli.parse.discover_source", return_value=mocker.MagicMock(path=Path()))
    caplog.set_level(logging.WARNING)
    monkeypatch.setenv("TOX_CONFIG_FILE", str(tmp_path))
    parsed, _, __, ___, ____ = get_options("r")
    msg = (
        "PermissionError(13, 'Permission denied')"
        if sys.platform == "win32"
        else "IsADirectoryError(21, 'Is a directory')"
    )
    assert caplog.messages == [f"failed to read config file {tmp_path} because {msg}"]
    default_options["config_file"] = tmp_path
    assert vars(parsed) == default_options


def test_bad_option_cli_ini(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    caplog: LogCaptureFixture,
    value_error: Callable[[str], str],
    default_options: Dict[str, Any],
) -> None:
    caplog.set_level(logging.WARNING)
    to = tmp_path / "tox.ini"
    to.write_text(
        textwrap.dedent(
            """
        [tox]
        verbose = what

        """,
        ),
    )
    monkeypatch.setenv("TOX_CONFIG_FILE", str(to))
    parsed, _, __, ___, ____ = get_options("r")
    assert caplog.messages == [
        "{} key verbose as type <class 'int'> failed with {}".format(
            to,
            value_error("invalid literal for int() with base 10: 'what'"),
        ),
    ]
    assert vars(parsed) == default_options
