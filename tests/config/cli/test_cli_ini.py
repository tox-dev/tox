import logging
import sys
import textwrap
from pathlib import Path
from typing import Callable, Dict

import pytest

from tox.config.cli.parse import get_options
from tox.config.loader.api import Override
from tox.pytest import CaptureFixture, LogCaptureFixture, MonkeyPatch
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


@pytest.fixture()
def empty_ini(tmp_path: Path, monkeypatch: MonkeyPatch) -> Path:
    to = tmp_path / "tox.ini"
    to.write_text(
        textwrap.dedent(
            """
        [tox]
        """,
        ),
    )
    monkeypatch.setenv("TOX_CONFIG_FILE", str(to))
    return to


def test_ini_empty(empty_ini: Path, core_handlers: Dict[str, Callable[[State], int]]) -> None:
    parsed, handlers, _ = get_options()
    assert vars(parsed) == {
        "colored": "no",
        "verbose": 2,
        "quiet": 0,
        "command": "run",
        "env": None,
        "default_runner": "virtualenv",
        "recreate": False,
        "no_test": False,
        "override": [],
    }
    assert parsed.verbosity == 2
    assert handlers == core_handlers


def test_ini_exhaustive_parallel_values(exhaustive_ini: Path, core_handlers: Dict[str, Callable[[State], int]]) -> None:
    parsed, handlers, _ = get_options()
    assert vars(parsed) == {
        "colored": "yes",
        "verbose": 5,
        "quiet": 1,
        "command": "run-parallel",
        "env": ["py37", "py36"],
        "default_runner": "virtualenv",
        "recreate": True,
        "no_test": True,
        "parallel": 3,
        "parallel_live": True,
        "override": [Override("a=b"), Override("c=d")],
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


def test_bad_cli_ini(tmp_path: Path, monkeypatch: MonkeyPatch, caplog: LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING)
    monkeypatch.setenv("TOX_CONFIG_FILE", str(tmp_path))
    parsed, __, _ = get_options()
    msg = (
        "PermissionError(13, 'Permission denied')"
        if sys.platform == "win32"
        else "IsADirectoryError(21, 'Is a directory')"
    )
    assert caplog.messages == [f"failed to read config file {tmp_path} because {msg}"]
    assert vars(parsed) == {
        "colored": "no",
        "verbose": 2,
        "quiet": 0,
        "command": "run",
        "override": [],
        "env": None,
        "default_runner": "virtualenv",
        "recreate": False,
        "no_test": False,
    }


def test_bad_option_cli_ini(
    tmp_path: Path, monkeypatch: MonkeyPatch, caplog: LogCaptureFixture, value_error: Callable[[str], str]
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
    parsed, _, __ = get_options()
    assert caplog.messages == [
        "{} key verbose as type <class 'int'> failed with {}".format(
            to,
            value_error("invalid literal for int() with base 10: 'what'"),
        ),
    ]
    assert vars(parsed) == {
        "colored": "no",
        "verbose": 2,
        "quiet": 0,
        "command": "run",
        "override": [],
        "env": None,
        "default_runner": "virtualenv",
        "recreate": False,
        "no_test": False,
    }
