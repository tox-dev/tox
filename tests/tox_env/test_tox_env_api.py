from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from unittest.mock import patch

import pytest

from tox.pytest import ToxProjectCreator
from tox.tox_env.api import ToxEnv


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
    out = rf".*py: failed with {fake_exe_on_path.stem} is not allowed, use allowlist_externals to allow it.*"
    result.assert_out_err(out=out, err="", regex=True)
    execute_calls.assert_called()


def test_env_log(tox_project: ToxProjectCreator) -> None:
    cmd = "commands=python -c 'import sys; print(1); print(2); print(3, file=sys.stderr); print(4, file=sys.stderr)'"
    prj = tox_project({"tox.ini": f"[testenv]\npackage=skip\n{cmd}"})
    result_first = prj.run("r")
    result_first.assert_success()

    log_dir = prj.path / ".tox" / "py" / "log"
    assert log_dir.exists(), result_first.out

    filename = {i.name for i in log_dir.iterdir()}
    assert filename == {"1-commands[0].log"}
    content = (log_dir / "1-commands[0].log").read_text()

    assert f"cwd: {prj.path}" in content
    assert f"allow: {prj.path}" in content
    assert "metadata " in content
    assert "env PATH: " in content
    assert content.startswith("name: py\nrun_id: commands[0]")
    assert "cmd: python -c" in content
    ending = """
    exit_code: 0
    1
    2

    standard error:
    3
    4
    """
    assert content.endswith(dedent(ending).lstrip()), content

    result_second = prj.run("r")  # second run overwrites, so no new files
    result_second.assert_success()
    filename = {i.name for i in log_dir.iterdir()}
    assert filename == {"1-commands[0].log"}


def test_tox_env_pass_env_literal_exist() -> None:
    with patch("os.environ", {"A": "1"}):
        env = ToxEnv._load_pass_env(["A"])
    assert env == {"A": "1"}


def test_tox_env_pass_env_literal_miss() -> None:
    with patch("os.environ", {}):
        env = ToxEnv._load_pass_env(["A"])
    assert not env


@pytest.mark.parametrize("glob", ["*", "?"])
@pytest.mark.parametrize("char", ["a", "A"])
def test_tox_env_pass_env_match_ignore_case(char: str, glob: str) -> None:
    with patch("os.environ", {"A1": "1", "a2": "2", "A2": "3", "B": "4"}):
        env = ToxEnv._load_pass_env([f"{char}{glob}"])
    assert env == {"A1": "1", "a2": "2", "A2": "3"}
