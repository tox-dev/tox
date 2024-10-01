from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tox.pytest import ToxProjectCreator


def test_cachedir_tag_created_in_new_workdir(tox_project: ToxProjectCreator) -> None:
    prj = tox_project({"tox.ini": "[testenv]\ncommands=python --version"})
    cwd = prj.path
    assert not (cwd / ".tox").exists()
    result = prj.run("run", from_cwd=cwd)
    result.assert_success()
    assert (cwd / ".tox" / "CACHEDIR.TAG").exists()


def test_cachedir_tag_not_created_in_extant_workdir(tox_project: ToxProjectCreator, tmp_path) -> None:
    workdir = tmp_path / "workworkwork"
    workdir.mkdir(parents=True)
    prj = tox_project({"tox.ini": "[testenv]\ncommands=python --version"})
    result = prj.run("--workdir", str(workdir), from_cwd=prj.path.parent)
    result.assert_success()
    assert not (workdir / "CACHEDIR.TAG").exists()
