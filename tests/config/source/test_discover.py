from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

import pytest

from tox.config.source.discover import discover_source
from tox.report import HandledError

if TYPE_CHECKING:
    from pathlib import Path

    from tox.pytest import ToxProjectCreator


# Root ignores the permission bits, and Windows does not model them this way,
# so the file stays readable and there is nothing to assert.
unreadable_files_possible = pytest.mark.skipif(
    sys.platform == "win32" or os.getuid() == 0,
    reason="cannot make a file unreadable as root or on Windows",
)


def out_no_src(path: Path) -> str:
    return (
        f"ROOT: No loadable tox.ini or setup.cfg or pyproject.toml or tox.toml found, assuming empty tox.ini at {path}"
        f"\ndefault environments:\npy -> [no description]\n"
    )


def test_no_src_cwd(tox_project: ToxProjectCreator) -> None:
    project = tox_project({})
    outcome = project.run("l")
    outcome.assert_success()
    assert outcome.out == out_no_src(project.path)
    assert outcome.state.conf.src_path == (project.path / "tox.ini")


def test_no_src_has_py_project_toml_above(tox_project: ToxProjectCreator, tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("")
    project = tox_project({})
    outcome = project.run("l")
    outcome.assert_success()
    assert outcome.out == out_no_src(tmp_path)
    assert outcome.state.conf.src_path == (tmp_path / "tox.ini")


def test_no_src_root_dir(tox_project: ToxProjectCreator, tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    project = tox_project({})
    outcome = project.run("l", "--root", str(root))
    outcome.assert_success()
    assert outcome.out == out_no_src(root)
    assert outcome.state.conf.src_path == (root / "tox.ini")


def test_bad_src_content(tox_project: ToxProjectCreator, tmp_path: Path) -> None:
    project = tox_project({})

    outcome = project.run("l", "-c", str(tmp_path / "setup.cfg"))
    outcome.assert_failed()
    assert outcome.out == f"ROOT: HandledError| config file {tmp_path / 'setup.cfg'} does not exist\n"


@unreadable_files_possible
@pytest.mark.parametrize("named", [True, False], ids=["explicit-path", "discovery"])
def test_unreadable_config_raises_handled_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, named: bool) -> None:
    """Reading the file raises an OSError subclass, not ValueError.

    Without handling it, discovery lets PermissionError escape and the CLI prints a traceback instead of the one-line
    error used for malformed files.

    This exercises discover_source directly: the tox_project fixture converts exceptions on its own, so it cannot tell
    the two cases apart.

    """
    config = tmp_path / "tox.ini"
    config.write_text("[tox]\nenv_list = py\n")
    config.chmod(0o000)
    monkeypatch.chdir(tmp_path)

    try:
        with pytest.raises(HandledError, match="failed loading"):
            discover_source(config if named else None, None)
    finally:
        config.chmod(0o644)


def test_malformed_config_does_not_prevent_help(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.toml": "deps =\n    mypy\n"})
    outcome = project.run("--help")
    outcome.assert_success()
    assert "usage: tox" in outcome.out


def test_malformed_toml_in_dir_reports_error(tox_project: ToxProjectCreator) -> None:
    """Config discovery in a directory should report TOML parse errors instead of silently ignoring them."""
    project = tox_project({})
    # Write a pyproject.toml with an invalid TOML escape sequence (unescaped backslash)
    (project.path / "pyproject.toml").write_text('[tool.tox]\ntest = "c:\\path"\n', encoding="utf-8")
    outcome = project.run("l", "-c", str(project.path))
    outcome.assert_failed()
    assert "failed loading" in outcome.out


def test_malformed_ini_in_dir_reports_error(tox_project: ToxProjectCreator) -> None:
    """Config discovery in a directory should report ini parse errors instead of raising a traceback."""
    project = tox_project({})
    # Write a tox.ini with an unterminated section header
    (project.path / "tox.ini").write_text("[tox\nenv_list = a\n", encoding="utf-8")
    outcome = project.run("l", "-c", str(project.path))
    outcome.assert_failed()
    assert "failed loading" in outcome.out
    assert "File contains no section headers" in outcome.out


@pytest.mark.parametrize(
    ("core_value", "message"),
    [
        pytest.param("min_version = notaversion", "min_version: Invalid version", id="min_version"),
        pytest.param("requires = ===bad!!!", "requires: Expected package name", id="requires"),
        pytest.param("env_list = {py39,py310", "env_list: {py39", id="env_list"),
    ],
)
def test_bad_ini_core_value_reports_error(tox_project: ToxProjectCreator, core_value: str, message: str) -> None:
    """A bad value in the ini core section should be a handled error rather than an unhandled traceback."""
    project = tox_project({"tox.ini": f"[tox]\n{core_value}\n"})
    outcome, leaked = None, None
    try:
        outcome = project.run("l")
    except Exception as exception:  # ruff:ignore[blind-except]  # a leaked traceback is the bug under test
        leaked = exception
    assert leaked is None, f"unhandled {type(leaked).__name__}: {leaked}"
    assert outcome is not None
    outcome.assert_failed()
    assert "failed to load tox." in outcome.out
    assert message in outcome.out


def test_toml_native_preferred_over_legacy_tox_ini(tox_project: ToxProjectCreator) -> None:
    """When pyproject.toml has both legacy_tox_ini and native TOML config, native TOML should win."""
    pyproject = """\
[tool.tox]
legacy_tox_ini = \"\"\"
[tox]
min_version = 4.21
[testenv]
commands = python -c "print('legacy')"
\"\"\"
env_list = ["native"]

[tool.tox.env_run_base]
package = "skip"
commands = [["python", "-c", "print('native')"]]
"""
    project = tox_project({"pyproject.toml": pyproject})
    outcome = project.run("l")
    outcome.assert_success()
    assert "native" in outcome.out
    assert "legacy" not in outcome.out
