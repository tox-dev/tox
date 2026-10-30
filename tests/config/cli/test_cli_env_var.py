from __future__ import annotations

from typing import TYPE_CHECKING, Final
from unittest.mock import ANY

import pytest

from tox.config.cli.env_var import get_env_var
from tox.config.cli.parse import get_options
from tox.config.loader.api import Override
from tox.session.env_select import CliEnv
from tox.util.ci import is_ci

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from tox.pytest import CaptureFixture, LogCaptureFixture, MonkeyPatch
    from tox.session.state import State


def test_verbose() -> None:
    parsed, _, __, ___, ____ = get_options("-v", "-v")
    assert parsed.verbosity == 4


def test_verbose_compound() -> None:
    parsed, _, __, ___, ____ = get_options("-vv")
    assert parsed.verbosity == 4


def test_verbose_no_test() -> None:
    parsed, _, __, ___, ____ = get_options("--notest", "-vv", "--runner", "virtualenv")
    assert vars(parsed) == {
        "verbose": 4,
        "quiet": 0,
        "colored": "no",
        "stderr_color": "RED",
        "work_dir": None,
        "root_dir": None,
        "config_file": None,
        "result_json": None,
        "no_capture": False,
        "command": "legacy",
        "default_runner": "virtualenv",
        "force_dep": [],
        "site_packages": False,
        "always_copy": False,
        "override": [],
        "show_config": False,
        "list_envs_all": False,
        "no_recreate_pkg": False,
        "no_provision": False,
        "list_envs": False,
        "devenv_path": None,
        "env": CliEnv(),
        "exit_and_dump_after": 0,
        "skip_missing_interpreters": "config",
        "skip_pkg_install": False,
        "skip_env_install": False,
        "recreate": False,
        "no_recreate_provision": False,
        "no_test": True,
        "package_only": False,
        "install_pkg": None,
        "fail_fast": False,
        "develop": False,
        "hash_seed": ANY,
        "discover": [],
        "parallel": 0,
        "parallel_live": False,
        "parallel_no_spinner": False,
        "pre": False,
        "factors": [],
        "labels": [],
        "skip_env": "",
        "list_dependencies": is_ci(),
        "remainder": [],
    }


def test_env_var_empty_list_is_empty(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("TOX_DISCOVER", "")
    assert get_env_var("discover", of_type=list[str]) == ([], "env var TOX_DISCOVER")


def test_env_var_exhaustive_parallel_values(
    monkeypatch: MonkeyPatch,
    core_handlers: dict[str, Callable[[State], int]],
) -> None:
    monkeypatch.setenv("TOX_COMMAND", "run-parallel")
    monkeypatch.setenv("TOX_VERBOSE", "5")
    monkeypatch.setenv("TOX_QUIET", "1")
    monkeypatch.setenv("TOX_ENV", "py37,py36")
    monkeypatch.setenv("TOX_DEFAULT_RUNNER", "virtualenv")
    monkeypatch.setenv("TOX_RECREATE", "yes")
    monkeypatch.setenv("TOX_NO_TEST", "yes")
    monkeypatch.setenv("TOX_PARALLEL", "3")
    monkeypatch.setenv("TOX_PARALLEL_LIVE", "no")
    monkeypatch.setenv("TOX_OVERRIDE", "a=b;c=d")
    monkeypatch.setenv("TOX_DISCOVER", "/foo/bar;/bar/baz;/baz/foo")

    options = get_options()
    assert vars(options.parsed) == {
        "always_copy": False,
        "colored": "no",
        "stderr_color": "RED",
        "command": "legacy",
        "default_runner": "virtualenv",
        "develop": False,
        "devenv_path": None,
        "discover": ["/foo/bar", "/bar/baz", "/baz/foo"],
        "env": CliEnv(["py37", "py36"]),
        "force_dep": [],
        "hash_seed": ANY,
        "install_pkg": None,
        "fail_fast": False,
        "no_provision": False,
        "list_envs": False,
        "list_envs_all": False,
        "no_recreate_pkg": False,
        "no_test": True,
        "no_capture": False,
        "override": [Override("a=b"), Override("c=d")],
        "package_only": False,
        "parallel": 3,
        "parallel_live": False,
        "parallel_no_spinner": False,
        "pre": False,
        "quiet": 1,
        "recreate": True,
        "no_recreate_provision": False,
        "result_json": None,
        "show_config": False,
        "site_packages": False,
        "skip_missing_interpreters": "config",
        "skip_pkg_install": False,
        "skip_env_install": False,
        "verbose": 5,
        "work_dir": None,
        "root_dir": None,
        "config_file": None,
        "factors": [],
        "labels": [],
        "exit_and_dump_after": 0,
        "skip_env": "",
        "list_dependencies": is_ci(),
        "remainder": [],
    }
    assert options.parsed.verbosity == 4
    assert options.cmd_handlers == core_handlers


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
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture,
    caplog: LogCaptureFixture,
    value_error: Callable[[str], str],
) -> None:
    monkeypatch.setenv("TOX_VERBOSE", "should-be-number")
    monkeypatch.setenv("TOX_QUIET", "1.00")
    parsed, _, __, ___, ____ = get_options()
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


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param("badoverride;testenv.commands=python deploy.py --password=hunter2", id="space-separated"),
        pytest.param("badoverride;--password=hunter2", id="semicolon-separated"),
    ],
)
def test_bad_env_var_redacts_secret(raw: str, monkeypatch: MonkeyPatch, capsys: CaptureFixture) -> None:
    monkeypatch.setenv("TOX_OVERRIDE", raw)
    get_options()
    out, err = capsys.readouterr()
    assert "hunter2" not in out + err
    assert "--password=*******" in out
    assert "badoverride;" in out


@pytest.mark.parametrize(
    ("secret", "mask"),
    [
        pytest.param("hunter2", "*******", id="plain"),
        pytest.param("hun ter2", "********", id="space"),
        pytest.param("hun\nter2", "********", id="newline"),
        pytest.param(r"hun\ter2", "********", id="backslash"),
        pytest.param("hun;ter2", "********", id="semicolon"),
    ],
)
def test_bad_env_var_redacts_secret_in_reason(
    secret: str, mask: str, monkeypatch: MonkeyPatch, capsys: CaptureFixture
) -> None:
    monkeypatch.setenv("TOX_PARALLEL", f"--password={secret}")
    get_options()
    out, err = capsys.readouterr()
    assert "hun" not in out + err
    assert "ter2" not in out + err
    assert f"--password={mask}" in out


@pytest.mark.parametrize(
    ("environment", "user_config"),
    [
        pytest.param(
            {"TOX_INSTALL_PKG": "../dist/demo-1.0-py3-none-any.whl"},
            "[tox]\n",
            id="environment",
        ),
        pytest.param(
            {},
            "[tox]\ninstall_pkg = ../dist/demo-1.0-py3-none-any.whl\n",
            id="user-config",
        ),
    ],
)
def test_install_pkg_relative_default_is_anchored(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    environment: dict[str, str],
    user_config: str,
) -> None:
    wheel: Final[Path] = tmp_path / "dist" / "demo-1.0-py3-none-any.whl"
    wheel.parent.mkdir()
    wheel.write_text("")
    (tmp_path / "tests").mkdir()
    monkeypatch.chdir(tmp_path / "tests")
    config_file: Final[Path] = tmp_path / "user.ini"
    config_file.write_text(user_config)
    monkeypatch.setenv("TOX_USER_CONFIG_FILE", str(config_file))
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    install_pkg: Final[Path | None] = get_options("r").parsed.install_pkg
    monkeypatch.chdir(tmp_path)
    assert install_pkg is not None
    assert install_pkg.resolve() == wheel


def test_install_pkg_env_var_file_uri(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    wheel: Final[Path] = tmp_path / "demo-1.0-py3-none-any.whl"
    wheel.write_text("")
    monkeypatch.setenv("TOX_INSTALL_PKG", wheel.as_uri())
    assert get_options("r").parsed.install_pkg == wheel
