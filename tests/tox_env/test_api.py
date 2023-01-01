from __future__ import annotations

from pathlib import Path

from tox.pytest import ToxProjectCreator


def test_ensure_temp_dir_exists(tox_project: ToxProjectCreator) -> None:
    ini = "[testenv]\ncommands=python -c 'import os; os.path.exists(r\"{temp_dir}\")'"
    project = tox_project({"tox.ini": ini})
    result = project.run()
    result.assert_success()


def test_dont_cleanup_temp_dir(tox_project: ToxProjectCreator, tmp_path: Path) -> None:
    (tmp_path / "foo" / "bar").mkdir(parents=True)
    project = tox_project({"tox.ini": "[tox]\ntemp_dir=foo"})
    result = project.run()
    result.assert_success()
    assert (tmp_path / "foo" / "bar").exists()
