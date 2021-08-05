import os
from pathlib import Path
from textwrap import dedent

from tox.pytest import ToxProjectCreator


def test_recreate(tox_project: ToxProjectCreator) -> None:
    prj = tox_project({"tox.ini": "[testenv]\npackage=skip\nrecreate=True"})
    result_first = prj.run("r")
    result_first.assert_success()

    result_second = prj.run("r")
    result_second.assert_success()
    assert "remove tox env folder" in result_second.out


def test_allow_list_external_fail(tox_project: ToxProjectCreator, fake_exe_on_path: Path) -> None:
    prj = tox_project({"tox.ini": f"[testenv]\npackage=skip\ncommands={fake_exe_on_path.stem}"})
    execute_calls = prj.patch_execute(lambda r: 0 if "cmd" in r.run_id else None)

    result = prj.run("r")

    result.assert_failed(1)
    out = fr".*py: failed with {fake_exe_on_path.stem} is not allowed, use allowlist_externals to allow it.*"
    result.assert_out_err(out=out, err="", regex=True)
    execute_calls.assert_called()


def test_env_log(tox_project: ToxProjectCreator) -> None:
    ini = "[testenv]\npackage=skip\ncommands=python -c 'import sys; print(1); print(2, file=sys.stderr)'"
    prj = tox_project({"tox.ini": ini})
    result_first = prj.run("r")
    result_first.assert_success()

    log_dir = prj.path / ".tox" / "4" / "py" / "log"
    assert log_dir.exists(), result_first.out

    filename = {i.name for i in log_dir.iterdir()}
    assert filename == {"1-commands[0].log"}
    content = (log_dir / "1-commands[0].log").read_text()

    assert f"cwd: {prj.path}" in content
    assert f"allow: {prj.path}" in content
    assert "metadata " in content
    assert "env PATH: " in content
    assert content.startswith(f"name: py{os.linesep}run_id: commands[0]")
    ending = """
    cmd: python -c 'import sys; print(1); print(2, file=sys.stderr)'
    exit_code: 0
    1

    standard error:
    2
    """
    assert content.endswith(dedent(ending).lstrip())

    result_second = prj.run("r")  # second run overwrites, so no new files
    result_second.assert_success()
    filename = {i.name for i in log_dir.iterdir()}
    assert filename == {"1-commands[0].log"}
