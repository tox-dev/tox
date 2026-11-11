from __future__ import annotations

from typing import TYPE_CHECKING

from tox.journal import EnvJournal
from tox.tox_env.package import PathPackage
from tox.tox_env.runner import RunToxEnv

if TYPE_CHECKING:
    from pathlib import Path

    from tox.pytest import ToxProjectCreator


def test_journal_package_empty() -> None:
    journal = EnvJournal(enabled=True, name="a")

    RunToxEnv._handle_journal_package(journal, [])  # ruff:ignore[private-member-access]  # empty package list

    content = journal.content
    assert content == {}


def test_journal_one_wheel_file(tmp_path: Path) -> None:
    wheel = tmp_path / "a.whl"
    wheel.write_bytes(b"magical")
    journal = EnvJournal(enabled=True, name="a")

    # A synthetic wheel keeps this digest check independent of a build backend.
    RunToxEnv._handle_journal_package(journal, [PathPackage(wheel)])  # ruff:ignore[private-member-access]

    content = journal.content
    assert content == {
        "installpkg": {
            "basename": "a.whl",
            "sha256": "0ce2d4c7087733c06b1087b28db95e114d7caeb515b841c6cdec8960cf884654",
            "type": "file",
        },
    }


def test_journal_multiple_wheel_file(tmp_path: Path) -> None:
    wheel_1 = tmp_path / "a.whl"
    wheel_1.write_bytes(b"magical")
    wheel_2 = tmp_path / "b.whl"
    wheel_2.write_bytes(b"magic")
    journal = EnvJournal(enabled=True, name="a")

    RunToxEnv._handle_journal_package(  # ruff:ignore[private-member-access]  # multiple packages
        journal, [PathPackage(wheel_1), PathPackage(wheel_2)]
    )

    content = journal.content
    assert content == {
        "installpkg": [
            {
                "basename": "a.whl",
                "sha256": "0ce2d4c7087733c06b1087b28db95e114d7caeb515b841c6cdec8960cf884654",
                "type": "file",
            },
            {
                "basename": "b.whl",
                "sha256": "3be7a505483c0050243c5cbad4700da13925aa4137a55e9e33efd8bc4d05850f",
                "type": "file",
            },
        ],
    }


def test_journal_package_dir(tmp_path: Path) -> None:
    journal = EnvJournal(enabled=True, name="a")

    # A synthetic directory checks journal metadata without installing it.
    RunToxEnv._handle_journal_package(journal, [PathPackage(tmp_path)])  # ruff:ignore[private-member-access]

    content = journal.content
    assert content == {
        "installpkg": {
            "basename": tmp_path.name,
            "type": "dir",
        },
    }


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


def test_recreate_commands_failure_does_not_block_recreation(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({
        "tox.toml": """
[env_run_base]
package = "skip"
recreate_commands = [["python", "-c", "raise SystemExit(1)"]]
commands = [["python", "-c", "print('MAIN')"]]
""",
    })
    proj.run("r").assert_success()

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
    proj.run("r").assert_success()

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
    proj.run("r").assert_success()

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
    proj.run("r").assert_success()

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
    execute_calls = proj.patch_execute(lambda request: 0 if "install" in request.run_id else None)
    proj.run("r", "--sdistonly").assert_success()

    found_calls = [(i[0][0].conf.name, i[0][3].run_id) for i in execute_calls.call_args_list]
    expected_calls = [
        (".pkg", "_optional_hooks"),
        (".pkg", "get_requires_for_build_sdist"),
        (".pkg", "get_requires_for_build_wheel"),
        (".pkg", "build_wheel"),
        (".pkg", "build_sdist"),
        (".pkg", "_exit"),
    ]
    assert found_calls == expected_calls
