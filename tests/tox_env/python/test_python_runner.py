from pathlib import Path

from packaging.requirements import Requirement

from tox.journal import EnvJournal
from tox.pytest import ToxProjectCreator
from tox.tox_env.python.api import Dep
from tox.tox_env.python.runner import PythonRun


def test_deps_config_path_req(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[testenv:py]\ndeps =-rpath.txt\n -r{toxinidir}/path.txt\n pytest"})
    result = project.run("c", "-e", "py")
    result.assert_success()
    deps = result.state.conf.get_env("py")["deps"]
    assert len(deps) == 3
    assert deps[0].value == project.path / "path.txt"
    assert deps[1].value == project.path / "path.txt"
    assert str(deps[2].value) == "pytest"


def test_journal_package_empty() -> None:
    journal = EnvJournal(enabled=True, name="a")

    PythonRun.handle_journal_package(journal, [])

    content = journal.content
    assert content == {}


def test_journal_one_wheel_file(tmp_path: Path) -> None:
    wheel = tmp_path / "a.whl"
    wheel.write_bytes(b"magical")
    journal = EnvJournal(enabled=True, name="a")

    PythonRun.handle_journal_package(journal, [Dep(wheel)])

    content = journal.content
    assert content == {
        "installpkg": {
            "basename": "a.whl",
            "sha256": "0ce2d4c7087733c06b1087b28db95e114d7caeb515b841c6cdec8960cf884654",
            "type": "file",
        }
    }


def test_journal_multiple_wheel_file(tmp_path: Path) -> None:
    wheel_1 = tmp_path / "a.whl"
    wheel_1.write_bytes(b"magical")
    wheel_2 = tmp_path / "b.whl"
    wheel_2.write_bytes(b"magic")
    journal = EnvJournal(enabled=True, name="a")

    PythonRun.handle_journal_package(journal, [Dep(wheel_1), Dep(wheel_2)])

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
        ]
    }


def test_journal_packge_dir(tmp_path: Path) -> None:
    journal = EnvJournal(enabled=True, name="a")

    PythonRun.handle_journal_package(journal, [Dep(tmp_path)])

    content = journal.content
    assert content == {
        "installpkg": {
            "basename": tmp_path.name,
            "type": "dir",
        }
    }


def test_journal_package_requirement(tmp_path: Path) -> None:
    journal = EnvJournal(enabled=True, name="a")

    PythonRun.handle_journal_package(journal, [Dep(Requirement("pytest"))])

    content = journal.content
    assert content == {}
