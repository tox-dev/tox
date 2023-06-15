from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from tox.pytest import ToxProjectCreator


def out_no_src(path: Path) -> str:
    return (
        f"ROOT: No tox.ini or setup.cfg or pyproject.toml found, assuming empty tox.ini at {path}\n"
        f"default environments:\npy -> [no description]\n"
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
    assert outcome.out == f"ROOT: HandledError| could not recognize config file {tmp_path / 'setup.cfg'}\n"
