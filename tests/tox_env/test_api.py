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
    ini = "[tox]\ntemp_dir={work_dir}/foo\n[testenv]\ncommands=python -c 'print(1)'"
    (tmp_path / "foo" / "bar").mkdir(parents=True)
    project = tox_project({"tox.ini": ini})
    result = project.run("--workdir", os.fspath(tmp_path))
    result.assert_success()
    assert os.path.exists(os.path.join(os.fspath(result.state.conf.core["temp_dir"]), "bar"))
