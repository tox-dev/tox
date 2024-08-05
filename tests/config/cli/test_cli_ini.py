from __future__ import annotations

import logging
import sys
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable
from unittest.mock import ANY

import pytest

from tox.config.cli.ini import IniConfig
from tox.config.cli.parse import get_options
from tox.config.cli.parser import Parsed
from tox.config.loader.api import Override
from tox.config.main import Config
from tox.config.source import discover_source
from tox.session.env_select import CliEnv
from tox.util.ci import is_ci

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from tox.pytest import CaptureFixture, LogCaptureFixture, MonkeyPatch
    from tox.session.state import State


@pytest.fixture
def default_options() -> dict[str, Any]:
    return {
        "colored": "no",
        "command": "r",
        "default_runner": "virtualenv",
        "develop": False,
        "discover": [],
        "env": CliEnv(),
        "hash_seed": ANY,
        "install_pkg": None,
        "no_test": False,
        "override": [],
        "package_only": False,
        "quiet": 0,
        "recreate": False,
        "no_recreate_provision": False,
        "no_provision": False,
        "no_recreate_pkg": False,
        "result_json": None,
        "skip_missing_interpreters": "config",
        "skip_pkg_install": False,
        "verbose": 2,
        "work_dir": None,
        "root_dir": None,
        "config_file": None,
        "factors": [],
        "labels": [],
        "exit_and_dump_after": 0,
        "skip_env": "",
        "list_dependencies": is_ci(),
    }


@pytest.mark.parametrize("content", ["[tox]", ""])
def test_ini_empty(  # noqa: PLR0913
    tmp_path: Path,
    core_handlers: dict[str, Callable[[State], int]],
    default_options: dict[str, Any],
    mocker: MockerFixture,
    monkeypatch: MonkeyPatch,
    content: str,
) -> None:
    to = tmp_path / "tox.ini"
    monkeypatch.setenv("TOX_USER_CONFIG_FILE", str(to))
    to.write_text(content)
    mocker.patch("tox.config.cli.parse.discover_source", return_value=mocker.MagicMock(path=Path()))
    options = get_options("r")
    assert vars(options.parsed) == default_options
    assert options.parsed.verbosity == 2
    assert options.cmd_handlers == core_handlers

    to.unlink()
    missing_options = get_options("r")
    missing_options.parsed.hash_seed = ANY
    assert vars(missing_options.parsed) == vars(options.parsed)


def test_bad_cli_ini(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    caplog: LogCaptureFixture,
    default_options: dict[str, Any],
    mocker: MockerFixture,
) -> None:
    mocker.patch("tox.config.cli.parse.discover_source", return_value=mocker.MagicMock(path=Path()))
    caplog.set_level(logging.WARNING)
    monkeypatch.setenv("TOX_USER_CONFIG_FILE", str(tmp_path))
    options = get_options("r")
    msg = (
        "PermissionError(13, 'Permission denied')"
        if sys.platform == "win32"
        else "IsADirectoryError(21, 'Is a directory')"
    )
    assert caplog.messages == [f"failed to read config file {tmp_path} because {msg}"]
    assert vars(options.parsed) == default_options


def test_bad_option_cli_ini(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    caplog: LogCaptureFixture,
    value_error: Callable[[str], str],
    default_options: dict[str, Any],
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
    monkeypatch.setenv("TOX_USER_CONFIG_FILE", str(to))
    parsed, _, __, ___, ____ = get_options("r")
    assert caplog.messages == [
        "{} key verbose as type <class 'int'> failed with {}".format(
            to,
            value_error("invalid literal for int() with base 10: 'what'"),
        ),
    ]
    assert vars(parsed) == default_options


def test_cli_ini_with_interpolated(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    to = tmp_path / "tox.ini"
    to.write_text("[tox]\na = %(b)s")
    monkeypatch.setenv("TOX_USER_CONFIG_FILE", str(to))
    conf = IniConfig()
    assert conf.get("a", str)


@pytest.mark.parametrize(
    ("conf_arg", "filename", "content"),
    [
        pytest.param("", "tox.ini", "[tox]", id="ini-dir"),
        pytest.param("tox.ini", "tox.ini", "[tox]", id="ini"),
        pytest.param("", "setup.cfg", "[tox:tox]", id="cfg-dir"),
        pytest.param("setup.cfg", "setup.cfg", "[tox:tox]", id="cfg"),
        pytest.param("", "pyproject.toml", '[tool.tox]\nlegacy_tox_ini = """\n[tox]\n"""\n', id="toml-dir"),
        pytest.param("pyproject.toml", "pyproject.toml", '[tool.tox]\nlegacy_tox_ini = """\n[tox]\n"""\n', id="toml"),
    ],
)
def test_conf_arg(tmp_path: Path, conf_arg: str, filename: str, content: str) -> None:
    dest = tmp_path / "c"
    dest.mkdir()
    if filename:
        cfg = dest / filename
        cfg.write_bytes(content.encode(encoding="utf-8"))

    config_file = dest / conf_arg
    source = discover_source(config_file, None)

    Config.make(
        Parsed(work_dir=dest, override=[], config_file=config_file, root_dir=None),
        pos_args=[],
        source=source,
    )


@pytest.fixture
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
    monkeypatch.setenv("TOX_USER_CONFIG_FILE", str(to))
    return to


@pytest.mark.usefixtures("exhaustive_ini")
def test_ini_exhaustive_parallel_values(core_handlers: dict[str, Callable[[State], int]]) -> None:
    options = get_options("p")
    assert vars(options.parsed) == {
        "colored": "yes",
        "command": "p",
        "default_runner": "virtualenv",
        "develop": False,
        "discover": [],
        "env": CliEnv(["py37", "py36"]),
        "hash_seed": ANY,
        "install_pkg": None,
        "no_test": True,
        "override": [Override("a=b"), Override("c=d")],
        "package_only": False,
        "no_recreate_pkg": False,
        "parallel": 3,
        "parallel_live": True,
        "parallel_no_spinner": False,
        "quiet": 1,
        "no_provision": False,
        "recreate": True,
        "no_recreate_provision": False,
        "result_json": None,
        "skip_missing_interpreters": "config",
        "skip_pkg_install": False,
        "verbose": 5,
        "work_dir": None,
        "root_dir": None,
        "config_file": None,
        "factors": [],
        "labels": [],
        "exit_and_dump_after": 0,
        "skip_env": "",
        "list_dependencies": is_ci(),
    }
    assert options.parsed.verbosity == 4
    assert options.cmd_handlers == core_handlers


def test_ini_help(exhaustive_ini: Path, capfd: CaptureFixture) -> None:
    with pytest.raises(SystemExit) as context:
        get_options("-h")
    assert context.value.code == 0
    out, err = capfd.readouterr()
    assert not err
    res = out.splitlines()[-1]
    msg = f"config file {str(exhaustive_ini)!r} active (changed via env var TOX_USER_CONFIG_FILE)"
    assert res == msg
