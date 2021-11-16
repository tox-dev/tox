from __future__ import annotations

from pathlib import Path

from tox.journal import EnvJournal
from tox.pytest import ToxProjectCreator
from tox.tox_env.package import PathPackage
from tox.tox_env.python.runner import PythonRun


def test_deps_config_path_req(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.ini": "[testenv:py]\ndeps =-rpath.txt\n -r {toxinidir}{/}path2.txt\n pytest",
            "path.txt": "alpha",
            "path2.txt": "beta",
        },
    )
    result = project.run("c", "-e", "py")
    result.assert_success()
    deps = result.state.conf.get_env("py")["deps"]
    assert deps.unroll() == ([], ["alpha", "beta", "pytest"])
    assert deps.as_root_args == ["pytest", "-r", "path.txt", "-r", str(project.path / "path2.txt")]
    assert str(deps) == f"-r {project.path / 'tox.ini'}"


def test_journal_package_empty() -> None:
    journal = EnvJournal(enabled=True, name="a")

    PythonRun._handle_journal_package(journal, [])

    content = journal.content
    assert content == {}


def test_journal_one_wheel_file(tmp_path: Path) -> None:
    wheel = tmp_path / "a.whl"
    wheel.write_bytes(b"magical")
    journal = EnvJournal(enabled=True, name="a")

    PythonRun._handle_journal_package(journal, [PathPackage(wheel)])

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

    PythonRun._handle_journal_package(journal, [PathPackage(wheel_1), PathPackage(wheel_2)])

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

    PythonRun._handle_journal_package(journal, [PathPackage(tmp_path)])

    content = journal.content
    assert content == {
        "installpkg": {
            "basename": tmp_path.name,
            "type": "dir",
        },
    }
