from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tox.pytest import ToxProjectCreator


def test_extra_setup_commands_runs_with_notest(tox_project: ToxProjectCreator) -> None:
    ini = """
        [testenv]
        package = skip
        deps = pip
        extra_setup_commands = python -c 'print("extra setup")'
        commands = python -c 'print("main command")'
    """
    proj = tox_project({"tox.ini": ini})
    result = proj.run("r", "--notest")
    result.assert_success()
    assert "extra setup" in result.out
    assert "main command" not in result.out


def test_extra_setup_commands_runs_without_notest(tox_project: ToxProjectCreator) -> None:
    ini = """
        [testenv]
        package = skip
        deps = pip
        extra_setup_commands = python -c 'print("extra setup")'
        commands = python -c 'print("main command")'
    """
    proj = tox_project({"tox.ini": ini})
    result = proj.run("r")
    result.assert_success()
    assert "extra setup" in result.out
    assert "main command" in result.out


def test_extra_setup_commands_with_package_skip(tox_project: ToxProjectCreator) -> None:
    ini = """
        [testenv]
        package = skip
        extra_setup_commands = python -c 'import sys; sys.exit(0)'
    """
    proj = tox_project({"tox.ini": ini})
    result = proj.run("r", "--notest")
    result.assert_success()


def test_extra_setup_commands_with_package_install(tox_project: ToxProjectCreator) -> None:
    ini = "[testenv]\nextra_setup_commands = python -c 'print(\"after package install\")'"
    proj = tox_project({"tox.ini": ini})
    result = proj.run("r", "--notest")
    result.assert_success()
    assert "after package install" in result.out


def test_extra_setup_commands_failure_stops_execution(tox_project: ToxProjectCreator) -> None:
    ini = """
        [testenv]
        package = skip
        extra_setup_commands = python -c 'import sys; sys.exit(1)'
        commands = python -c 'print("should not run")'
    """
    proj = tox_project({"tox.ini": ini})
    result = proj.run("r", "--notest")
    result.assert_failed()
    assert "extra_setup_commands failed" in result.out


def test_extra_setup_commands_failure_with_ignore_errors(tox_project: ToxProjectCreator) -> None:
    ini = """
        [testenv]
        package = skip
        ignore_errors = true
        extra_setup_commands = python -c 'import sys; sys.exit(1)'
        commands = python -c 'print("main command")'
    """
    proj = tox_project({"tox.ini": ini})
    result = proj.run("r")
    result.assert_success()
    assert "main command" in result.out


def test_extra_setup_commands_multiple_commands(tox_project: ToxProjectCreator) -> None:
    ini = """
        [testenv]
        package = skip
        extra_setup_commands =
            python -c 'print("cmd1")'
            python -c 'print("cmd2")'
            python -c 'print("cmd3")'
    """
    proj = tox_project({"tox.ini": ini})
    result = proj.run("r", "--notest")
    result.assert_success()
    assert "cmd1" in result.out
    assert "cmd2" in result.out
    assert "cmd3" in result.out


def test_extra_setup_commands_empty_default(tox_project: ToxProjectCreator) -> None:
    ini = "[testenv]\npackage = skip"
    proj = tox_project({"tox.ini": ini})
    result = proj.run("r", "--notest")
    result.assert_success()


def test_extra_setup_commands_execution_order(tox_project: ToxProjectCreator) -> None:
    ini = """
        [testenv]
        package = skip
        deps = pip
        extra_setup_commands = python -c 'print("EXTRA_SETUP")'
        commands_pre = python -c 'print("COMMANDS_PRE")'
        commands = python -c 'print("COMMANDS")'
        commands_post = python -c 'print("COMMANDS_POST")'
    """
    proj = tox_project({"tox.ini": ini})
    result = proj.run("r")
    result.assert_success()

    assert "EXTRA_SETUP" in result.out
    assert "COMMANDS_PRE" in result.out
    assert "COMMANDS" in result.out
    assert "COMMANDS_POST" in result.out

    lines = result.out.split("\n")
    extra_setup_idx = next(i for i, line in enumerate(lines) if "EXTRA_SETUP" in line)
    commands_pre_idx = next(i for i, line in enumerate(lines) if "COMMANDS_PRE" in line)
    commands_idx = next(
        i
        for i, line in enumerate(lines)
        if "COMMANDS" in line and "COMMANDS_PRE" not in line and "COMMANDS_POST" not in line
    )
    commands_post_idx = next(i for i, line in enumerate(lines) if "COMMANDS_POST" in line)

    assert extra_setup_idx < commands_pre_idx < commands_idx < commands_post_idx
