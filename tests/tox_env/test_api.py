import os.path
from pathlib import Path

from tox.pytest import ToxProjectCreator


def test_ensure_temp_dir_exists(tox_project: ToxProjectCreator) -> None:
    ini = "[testenv]\ncommands=python -c 'print(1)'"
    project = tox_project({"tox.ini": ini})
    result = project.run()
    result.assert_success()
    assert result.state.conf.core["temp_dir"].exists()


def test_dont_cleanup_temp_dir(tox_project: ToxProjectCreator, tmp_path: Path) -> None:
    ini = f"[tox]\ntemp_dir={tmp_path}\n[testenv]\ncommands=python -c 'print(1)'"
    (tmp_path / "foo").touch()
    project = tox_project({"tox.ini": ini})
    result = project.run()
    result.assert_success()
    assert os.path.exists(os.path.join(result.state.conf.core["temp_dir"], "foo"))
