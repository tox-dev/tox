from __future__ import annotations

import os
from textwrap import dedent
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from tox.tox_env.api import ToxEnv

if TYPE_CHECKING:
    from pathlib import Path

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
    out = rf".*py: failed with {fake_exe_on_path.stem} is not allowed, use allowlist_externals to allow it.*"
    result.assert_out_err(out=out, err="", regex=True)
    execute_calls.assert_called()


def test_env_log(tox_project: ToxProjectCreator) -> None:
    cmd = "commands=python -c 'import sys; print(1); print(2); print(3, file=sys.stderr); print(4, file=sys.stderr)'"
    env_vars = "    UNPREDICTABLE = 🪟"
    prj = tox_project({"tox.ini": f"[testenv]\npackage=skip\nset_env =\n{env_vars}\n{cmd}"})
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
        env = ToxEnv._load_pass_env(["A"])  # noqa: SLF001
    assert env == {"A": "1"}


def test_tox_env_pass_env_literal_miss() -> None:
    with patch("os.environ", {}):
        env = ToxEnv._load_pass_env(["A"])  # noqa: SLF001
    assert not env


def test_tox_env_pass_env_fails_on_whitespace(tox_project: ToxProjectCreator) -> None:
    first, second = "A B", "C D"
    prj = tox_project({"tox.ini": f"[testenv]\npackage=skip\npass_env = {first}\n {second}\n  E"})
    result = prj.run("c", "-k", "pass_env", raise_on_config_fail=False)
    result.assert_failed(code=-1)
    msg = (
        '[testenv:py]\npass_env = # Exception: Fail("pass_env values cannot contain whitespace, use comma to have '
        f'multiple values in a single line, invalid values found {first!r}, {second!r}")\n'
    )
    assert result.out == msg

    result = prj.run("r")
    result.assert_failed(1)
    msg = (
        "py: failed with pass_env values cannot contain whitespace, use comma to have multiple values in a single line,"
        " invalid values found 'A B', 'C D'"
    )
    assert msg in result.out


@pytest.mark.parametrize("glob", ["*", "?"])
@pytest.mark.parametrize("char", ["a", "A"])
def test_tox_env_pass_env_match_ignore_case(char: str, glob: str) -> None:
    with patch("os.environ", {"A1": "1", "a2": "2", "A2": "3", "B": "4"}):
        env = ToxEnv._load_pass_env([f"{char}{glob}"])  # noqa: SLF001
    assert env == {"A1": "1", "a2": "2", "A2": "3"}


def test_disallow_pass_env(tox_project: ToxProjectCreator) -> None:
    cmd = "import os; print(os.environ.get('FOO_BAR', '')); print(os.environ.get('FOO_SECRET', ''))"
    toml = f"""
    [env_run_base]
    package = "skip"
    pass_env = ["FOO_*"]
    disallow_pass_env = ["FOO_SECRET"]
    commands = [["python", "-c", "{cmd}"]]
    """
    project = tox_project({"tox.toml": toml})
    with patch.dict("os.environ", {"FOO_BAR": "visible", "FOO_SECRET": "hidden"}):
        result = project.run("r")
    result.assert_success()
    assert "visible" in result.out
    assert "hidden" not in result.out


def test_disallow_pass_env_glob(tox_project: ToxProjectCreator) -> None:
    cmd = "import os; print(os.environ.get('APP_NAME', '')); print(os.environ.get('APP_SECRET_KEY', ''))"
    toml = f"""
    [env_run_base]
    package = "skip"
    pass_env = ["APP_*"]
    disallow_pass_env = ["APP_SECRET_*"]
    commands = [["python", "-c", "{cmd}"]]
    """
    project = tox_project({"tox.toml": toml})
    with patch.dict("os.environ", {"APP_NAME": "myapp", "APP_SECRET_KEY": "s3cret"}):
        result = project.run("r")
    result.assert_success()
    assert "myapp" in result.out
    assert "s3cret" not in result.out


def test_disallow_pass_env_empty(tox_project: ToxProjectCreator) -> None:
    toml = """
    [env_run_base]
    package = "skip"
    pass_env = ["FOO"]
    commands = [["python", "-c", "import os; print(os.environ.get('FOO', ''))"]]
    """
    project = tox_project({"tox.toml": toml})
    with patch.dict("os.environ", {"FOO": "bar"}):
        result = project.run("r")
    result.assert_success()
    assert "bar" in result.out


def test_change_dir_posargs_no_recursion(tox_project: ToxProjectCreator) -> None:
    toml = """\
[env.foo]
package = "skip"
change_dir = "{posargs}"
commands = [["python", "--version"]]
"""
    prj = tox_project({"tox.toml": toml})
    (prj.path / "subdir").mkdir()
    result = prj.run("r", "-e", "foo", "--", "subdir")
    result.assert_success()
    assert f"foo: commands[0] {prj.path / 'subdir'}>" in result.out


def test_posargs_cross_drive_no_crash(tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch) -> None:
    toml = """\
[env_run_base]
package = "skip"
commands = [["python", "{posargs}"]]
"""
    prj = tox_project({"tox.toml": toml})
    (prj.path / "test.py").write_text("print('ok')")
    original_relpath = os.path.relpath

    def _relpath_cross_drive(path: str, start: str) -> str:
        if "test.py" in path:
            msg = "path is on mount 'O:', start on mount 'C:'"
            raise ValueError(msg)
        return original_relpath(path, start)

    monkeypatch.setattr(os.path, "relpath", _relpath_cross_drive)
    result = prj.run("r", "--", "test.py")
    result.assert_success()
    assert "ok" in result.out


def test_change_dir_is_created_if_not_exist(tox_project: ToxProjectCreator) -> None:
    prj = tox_project({"tox.ini": "[testenv]\npackage=skip\nchange_dir=a{/}b\ncommands=python --version"})
    result_first = prj.run("r")
    result_first.assert_success()
    assert (prj.path / "a" / "b").exists()


def test_change_dir_is_relative_to_conf(tox_project: ToxProjectCreator) -> None:
    prj = tox_project({"tox.ini": "[testenv]\npackage=skip\nchange_dir=a"})
    result = prj.run("c", "-e", "py", "-k", "change_dir", "-c", prj.path.name, from_cwd=prj.path.parent)
    result.assert_success()
    lines = result.out.splitlines()
    assert lines[1] == f"change_dir = {prj.path / 'a'}"


def test_setenv_path_not_overwritten(tox_project: ToxProjectCreator) -> None:
    cmd = "import os; print(os.environ['PATH'])"
    toml = f"""
    [env_run_base]
    package = "skip"
    set_env.PATH = "{{env:PATH}}:/custom/test/path"
    commands = [["python", "-c", "{cmd}"]]
    """
    project = tox_project({"tox.toml": toml})
    result = project.run("r")
    result.assert_success()
    # The custom path from set_env must survive — not be overwritten
    assert "/custom/test/path" in result.out


def test_setenv_path_venv_paths_first(tox_project: ToxProjectCreator) -> None:
    cmd = "import os; print(os.environ['PATH'])"
    toml = f"""
    [env_run_base]
    package = "skip"
    set_env.PATH = "{{env:PATH}}:/trailing/path"
    commands = [["python", "-c", "{cmd}"]]
    """
    project = tox_project({"tox.toml": toml})
    result = project.run("r")
    result.assert_success()
    path_line = next(line for line in result.out.splitlines() if "/trailing/path" in line)
    path_entries = path_line.split(":")
    # The virtual environment paths (containing .tox) must come before the trailing path
    tox_idx = next((i for i, p in enumerate(path_entries) if ".tox" in p), None)
    trailing_idx = next(i for i, p in enumerate(path_entries) if p == "/trailing/path")
    assert tox_idx is not None, f"expected .tox path in PATH, got: {path_line}"
    assert tox_idx < trailing_idx, f"venv paths should precede trailing path: {path_line}"


def test_cachedir_tag_created(tox_project: ToxProjectCreator) -> None:
    prj = tox_project({"tox.ini": "[testenv]\npackage=skip"})
    result = prj.run("r")
    result.assert_success()

    tag = prj.path / ".tox" / "CACHEDIR.TAG"
    assert tag.is_file()
    content = tag.read_text(encoding="utf-8")
    assert content.startswith("Signature: 8a477f597d28d172789f06886806bc55\n")
