from __future__ import annotations

import os
from shutil import rmtree
from textwrap import dedent
from typing import TYPE_CHECKING, Final
from unittest.mock import patch

import pytest
from filelock import BaseFileLock

from tox.tox_env.api import ToxEnv

if TYPE_CHECKING:
    from pathlib import Path

    from tox.pytest import ToxProject, ToxProjectCreator, ToxRunOutcome


def test_recreate(tox_project: ToxProjectCreator) -> None:
    prj = tox_project({"tox.ini": "[testenv]\npackage=skip\nrecreate=True"})
    result_first = prj.run("r")
    result_first.assert_success()

    result_second = prj.run("r")
    result_second.assert_success()
    assert "remove tox env folder" in result_second.out


@pytest.mark.skipif(os.name == "nt", reason="creating symlinks needs privileges on Windows")
def test_env_symlink_fails_without_recreate(tox_project: ToxProjectCreator, tmp_path: Path) -> None:
    project: Final = tox_project({"tox.ini": "[testenv]\npackage=skip"})
    outside: Final = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep").write_text("keep")
    env_dir: Final = project.path / ".tox" / "py"
    env_dir.parent.mkdir()
    env_dir.symlink_to(outside, target_is_directory=True)

    result: Final = project.run("r")

    result.assert_failed()
    assert "is a symlink where this environment should live" in result.out
    assert (outside / "keep").read_text() == "keep"


@pytest.mark.skipif(os.name == "nt", reason="creating symlinks needs privileges on Windows")
@pytest.mark.parametrize("command", [pytest.param(("l",), id="list"), pytest.param(("r", "--notest"), id="run")])
def test_package_env_symlink_not_locked_through(
    tox_project: ToxProjectCreator, tmp_path: Path, command: tuple[str, ...]
) -> None:
    project: Final = tox_project({
        "tox.ini": "[tox]\nenv_list = py\n[testenv]\ncommands = python -c 'print(1)'",
        "pyproject.toml": '[build-system]\nrequires = ["setuptools"]\nbuild-backend = "setuptools.build_meta"',
    })
    outside: Final = tmp_path / "outside"
    outside.mkdir()
    pkg_dir: Final = project.path / ".tox" / ".pkg"
    pkg_dir.parent.mkdir()
    pkg_dir.symlink_to(outside, target_is_directory=True)
    acquire: Final = BaseFileLock.acquire

    with patch.object(BaseFileLock, "acquire", autospec=True, side_effect=acquire) as acquire_spy:
        project.run(*command)

    assert pkg_dir.is_symlink()
    assert list(outside.iterdir()) == []
    assert [c.args[0].lock_file for c in acquire_spy.call_args_list if str(pkg_dir) in c.args[0].lock_file] == []


@pytest.mark.skipif(os.name == "nt", reason="creating symlinks needs privileges on Windows")
@pytest.mark.parametrize("target_files", [pytest.param(("keep",), id="existing"), pytest.param((), id="dangling")])
def test_env_symlink_recreated_without_touching_target(
    tox_project: ToxProjectCreator, tmp_path: Path, target_files: tuple[str, ...]
) -> None:
    project: Final = tox_project({"tox.ini": "[testenv]\npackage=skip"})
    outside: Final = tmp_path / "outside"
    for filename in target_files:
        outside.mkdir()
        (outside / filename).write_text("keep")
    env_dir: Final = project.path / ".tox" / "py"
    env_dir.parent.mkdir()
    env_dir.symlink_to(outside, target_is_directory=True)

    project.run("r", "-r").assert_success()

    assert env_dir.is_dir()
    assert not env_dir.is_symlink()
    assert [(entry.name, entry.read_text()) for entry in outside.glob("*")] == [
        (filename, "keep") for filename in target_files
    ]


@pytest.mark.skipif(os.name == "nt", reason="creating symlinks needs privileges on Windows")
@pytest.mark.parametrize("name", [pytest.param("log", id="log"), pytest.param("tmp", id="tmp")])
def test_env_child_symlink_replaced_without_touching_target(
    tox_project: ToxProjectCreator, tmp_path: Path, name: str
) -> None:
    project: Final = tox_project({"tox.ini": "[testenv]\npackage=skip\ncommands=python -c 'print(1)'"})
    project.run("r").assert_success()
    outside: Final = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep").write_text("keep")
    child: Final = project.path / ".tox" / "py" / name
    rmtree(child)
    child.symlink_to(outside, target_is_directory=True)

    project.run("r").assert_success()

    assert child.is_dir()
    assert not child.is_symlink()
    assert (outside / "keep").read_text() == "keep"


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


def test_env_log_cleared_without_commands(tox_project: ToxProjectCreator) -> None:
    config = '[env_run_base]\npackage = "skip"\n'
    prj = tox_project({"tox.toml": config + 'commands = [["python", "-c", "pass"]]\n'})
    prj.run("r").assert_success()

    log_dir = prj.path / ".tox" / "py" / "log"
    assert {path.name for path in log_dir.iterdir()} == {"1-commands[0].log"}

    (prj.path / "tox.toml").write_text(config + "commands = []\n")
    prj.run("r").assert_success()

    assert not list(log_dir.iterdir())


def test_env_log_redacts_secret_argv(tox_project: ToxProjectCreator) -> None:
    cmd = "commands=python -c 'pass' --token=hunter2 --cov=tox"
    prj = tox_project({"tox.ini": f"[testenv]\npackage=skip\n{cmd}"})
    result = prj.run("r")
    result.assert_success()
    log_dir = prj.path / ".tox" / "py" / "log"
    content = (log_dir / "1-commands[0].log").read_text()
    cmd_line = next(line for line in content.splitlines() if line.startswith("cmd:"))
    assert "hunter2" not in cmd_line
    assert "--token=*******" in cmd_line
    assert "--cov=tox" in cmd_line  # innocuous flags untouched
    assert "hunter2" not in result.out  # also masked in the LOGGER warning shown to the user


def test_env_log_redacts_secret_argv_after_open_quote(
    tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GIT_REF", "it's")
    monkeypatch.setenv("DEPLOY_TOKEN", "hunter2")
    prj = tox_project({
        "tox.ini": ("[testenv]\npackage=skip\ncommands=python -c 'pass' --ref={env:GIT_REF} --token={env:DEPLOY_TOKEN}")
    })
    result = prj.run("r")
    result.assert_success()
    content = (prj.path / ".tox" / "py" / "log" / "1-commands[0].log").read_text()
    assert "hunter2" not in content
    assert "--token=*******" in content
    assert "hunter2" not in result.out
    assert "--token=*******" in result.out


def test_tox_env_pass_env_literal_exist() -> None:
    with patch("os.environ", {"A": "1"}):
        env = ToxEnv._load_pass_env(["A"])  # ruff:ignore[private-member-access]
    assert env == {"A": "1"}


def test_tox_env_pass_env_literal_miss() -> None:
    with patch("os.environ", {}):
        env = ToxEnv._load_pass_env(["A"])  # ruff:ignore[private-member-access]
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
        env = ToxEnv._load_pass_env([f"{char}{glob}"])  # ruff:ignore[private-member-access]
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


@pytest.mark.parametrize(
    ("key", "path"),
    [
        pytest.param("env_dir", "e", id="environment"),
        pytest.param("env_tmp_dir", "t", id="temporary"),
        pytest.param("env_log_dir", "l", id="log"),
    ],
)
def test_env_dirs_are_relative_to_conf(tox_project: ToxProjectCreator, key: str, path: str) -> None:
    ini: Final[str] = "[testenv]\npackage=skip\nenv_dir=e\nenv_tmp_dir=t\nenv_log_dir=l\ncommands=python --version"
    project: Final[ToxProject] = tox_project({"tox.ini": ini})
    result: Final[ToxRunOutcome] = project.run(
        "c", "-e", "py", "-k", key, "-c", project.path.name, from_cwd=project.path.parent
    )
    result.assert_success()
    assert result.env_conf("py")[key] == project.path / path


def test_relative_env_dirs_leave_start_dir_untouched(tox_project: ToxProjectCreator) -> None:
    ini: Final[str] = "[testenv]\npackage=skip\nenv_dir=e\nenv_tmp_dir=t\nenv_log_dir=l\ncommands=python --version"
    project: Final[ToxProject] = tox_project({"tox.ini": ini})
    kept: Final[list[Path]] = [project.path.parent / name / "keep" for name in ("e", "t", "l")]
    for file in kept:
        file.parent.mkdir()
        file.write_text("")

    result: Final[ToxRunOutcome] = project.run(
        "r", "-r", "-e", "py", "-c", project.path.name, from_cwd=project.path.parent
    )

    result.assert_success()
    assert all(file.exists() for file in kept)


def test_env_dir_absolute_is_kept(tox_project: ToxProjectCreator, tmp_path: Path) -> None:
    prj: Final[ToxProject] = tox_project({"tox.ini": f"[testenv]\npackage=skip\nenv_dir={tmp_path / 'e'}"})
    result: Final[ToxRunOutcome] = prj.run("c", "-e", "py", "-k", "env_dir")
    result.assert_success()
    assert result.env_conf("py")["env_dir"] == tmp_path / "e"


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


def test_gitignore_created_in_work_dir(tox_project: ToxProjectCreator) -> None:
    prj = tox_project({"tox.ini": "[testenv]\npackage=skip\ncommands=python -c 'print(1)'"})
    result = prj.run("r")
    result.assert_success()
    gitignore = prj.path / ".tox" / ".gitignore"
    assert gitignore.exists()
    assert gitignore.read_text(encoding="utf-8") == "*\n"
