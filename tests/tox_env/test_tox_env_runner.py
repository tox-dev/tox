from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from tox.pytest import ToxProjectCreator


def test_recreate_commands_run_on_recreate(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({
        "tox.toml": """
[env_run_base]
package = "skip"
recreate_commands = [["python", "-c", "print('RECREATE_CLEANUP')"]]
commands = [["python", "-c", "print('MAIN')"]]
""",
    })
    first = proj.run("r")
    first.assert_success()
    assert "RECREATE_CLEANUP" not in first.out

    second = proj.run("r", "-r")
    second.assert_success()
    assert "RECREATE_CLEANUP" in second.out
    assert "MAIN" in second.out


def test_recreate_commands_not_run_on_first_creation(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({
        "tox.toml": """
[env_run_base]
package = "skip"
recreate_commands = [["python", "-c", "print('RECREATE_CLEANUP')"]]
""",
    })
    result = proj.run("r")
    result.assert_success()
    assert "RECREATE_CLEANUP" not in result.out


def test_recreate_commands_failure_does_not_block_recreation(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({
        "tox.toml": """
[env_run_base]
package = "skip"
recreate_commands = [["python", "-c", "raise SystemExit(1)"]]
commands = [["python", "-c", "print('MAIN')"]]
""",
    })
    first = proj.run("r")
    first.assert_success()

    second = proj.run("r", "-r")
    second.assert_success()
    assert "MAIN" in second.out


def test_recreate_commands_not_run_without_recreate(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({
        "tox.toml": """
[env_run_base]
package = "skip"
recreate_commands = [["python", "-c", "print('RECREATE_CLEANUP')"]]
commands = [["python", "-c", "print('MAIN')"]]
""",
    })
    first = proj.run("r")
    first.assert_success()

    second = proj.run("r")
    second.assert_success()
    assert "RECREATE_CLEANUP" not in second.out
    assert "MAIN" in second.out


def test_recreate_commands_multiple(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({
        "tox.toml": """
[env_run_base]
package = "skip"
recreate_commands = [
    ["python", "-c", "print('CLEANUP_1')"],
    ["python", "-c", "print('CLEANUP_2')"],
]
commands = [["python", "-c", "print('MAIN')"]]
""",
    })
    first = proj.run("r")
    first.assert_success()

    second = proj.run("r", "-r")
    second.assert_success()
    assert "CLEANUP_1" in second.out
    assert "CLEANUP_2" in second.out
    assert "MAIN" in second.out


def test_recreate_commands_run_before_env_removed(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({
        "tox.toml": """
[env_run_base]
package = "skip"
recreate_commands = [["python", "-c", "print('RECREATE_CLEANUP')"]]
commands = [["python", "-c", "print('MAIN')"]]
""",
    })
    first = proj.run("r")
    first.assert_success()

    second = proj.run("r", "-r")
    second.assert_success()
    lines = second.out.split("\n")
    cleanup_idx = next(i for i, line in enumerate(lines) if "RECREATE_CLEANUP" in line)
    remove_idx = next(i for i, line in enumerate(lines) if "remove tox env folder" in line)
    assert cleanup_idx < remove_idx


def test_package_only(
    tox_project: ToxProjectCreator,
    demo_pkg_inline: Path,
) -> None:
    ini = "[testenv]\ncommands = python -c 'print('foo')'"
    proj = tox_project(
        {"tox.ini": ini, "pyproject.toml": (demo_pkg_inline / "pyproject.toml").read_text()},
        base=demo_pkg_inline,
    )
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("r", "--sdistonly")
    result.assert_success()

    expected_calls = [
        (".pkg", "_optional_hooks"),
        (".pkg", "get_requires_for_build_sdist"),
        (".pkg", "get_requires_for_build_wheel"),
        (".pkg", "build_wheel"),
        (".pkg", "build_sdist"),
        (".pkg", "_exit"),
    ]
    found_calls = [(i[0][0].conf.name, i[0][3].run_id) for i in execute_calls.call_args_list]
    assert found_calls == expected_calls
