from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from tox.pytest import ToxProjectCreator


def _tox_ini(extra: str = "") -> str:
    lines = ["[testenv:check]", "runner = virtualenv-pep-723", "script = check.py"]
    if extra:
        lines.append(extra)
    return "\n".join(lines) + "\n"


def _run(project: ToxProjectCreator, files: dict[str, str], *extra_args: str) -> tuple:
    proj = project(files)
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("r", "-e", "check", "--discover", sys.executable, *extra_args)
    return result, execute_calls


def _py_ver() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}"


def test_deps_installed(tox_project: ToxProjectCreator) -> None:
    script = "# /// script\n# dependencies = [\"setuptools\"]\n# ///\nprint('ok')\n"
    result, execute_calls = _run(tox_project, {"tox.ini": _tox_ini(), "check.py": script})
    result.assert_success()
    install_cmds = [i[0][3].cmd for i in execute_calls.call_args_list if "install" in i[0][3].run_id]
    assert any("setuptools" in arg for cmd in install_cmds for arg in cmd)


def test_no_deps_when_only_requires_python(tox_project: ToxProjectCreator) -> None:
    script = f'# /// script\n# requires-python = ">={_py_ver()}"\n# ///\nprint("ok")\n'
    result, execute_calls = _run(tox_project, {"tox.ini": _tox_ini(), "check.py": script})
    result.assert_success()
    assert not [i for i in execute_calls.call_args_list if "install" in i[0][3].run_id]


def test_no_deps_when_no_metadata(tox_project: ToxProjectCreator) -> None:
    result, execute_calls = _run(tox_project, {"tox.ini": _tox_ini(), "check.py": 'print("ok")\n'})
    result.assert_success()
    assert not [i for i in execute_calls.call_args_list if "install" in i[0][3].run_id]


def test_custom_commands_override(tox_project: ToxProjectCreator) -> None:
    script = "# /// script\n# dependencies = [\"setuptools\"]\n# ///\nprint('ok')\n"
    result, execute_calls = _run(
        tox_project,
        {"tox.ini": _tox_ini("commands = python -c \"print('custom')\""), "check.py": script},
    )
    result.assert_success()
    cmd_calls = [i[0][3].cmd for i in execute_calls.call_args_list if i[0][3].run_id == "commands[0]"]
    assert any("custom" in str(cmd) for cmd in cmd_calls)


def test_default_commands_forward_posargs(tox_project: ToxProjectCreator) -> None:
    result, execute_calls = _run(
        tox_project, {"tox.ini": _tox_ini(), "check.py": 'print("ok")\n'}, "--", "arg1", "arg2"
    )
    result.assert_success()
    cmd = next(i[0][3].cmd for i in execute_calls.call_args_list if i[0][3].run_id == "commands[0]")
    assert "arg1" in cmd
    assert "arg2" in cmd


def test_requires_python_satisfied(tox_project: ToxProjectCreator) -> None:
    script = f'# /// script\n# requires-python = ">={_py_ver()}"\n# ///\nprint("ok")\n'
    result, _ = _run(tox_project, {"tox.ini": _tox_ini(), "check.py": script})
    result.assert_success()


def test_requires_python_not_satisfied(tox_project: ToxProjectCreator) -> None:
    script = '# /// script\n# requires-python = ">=99.0"\n# ///\nprint("ok")\n'
    result, _ = _run(tox_project, {"tox.ini": _tox_ini(), "check.py": script})
    result.assert_failed()
    assert "does not satisfy requires-python" in result.out


def test_skip_env_install(tox_project: ToxProjectCreator) -> None:
    script = "# /// script\n# dependencies = [\"setuptools\"]\n# ///\nprint('ok')\n"
    result, execute_calls = _run(tox_project, {"tox.ini": _tox_ini(), "check.py": script}, "--skip-env-install")
    result.assert_success()
    assert not [i for i in execute_calls.call_args_list if "install" in i[0][3].run_id]


@pytest.mark.parametrize(
    ("script", "error_fragment"),
    [
        pytest.param(
            '# /// script\n# requires-python = ">=3.12"\n# ///\n\n# /// script\n# dependencies = []\n# ///\n',
            "multiple",
            id="multiple-script-blocks",
        ),
        pytest.param(
            "# /// script\n# requires-python = not valid toml\n# ///\n",
            "Invalid",
            id="malformed-toml",
        ),
    ],
)
def test_invalid_script_metadata(tox_project: ToxProjectCreator, script: str, error_fragment: str) -> None:
    result, _ = _run(tox_project, {"tox.ini": _tox_ini(), "check.py": script})
    result.assert_failed()
    assert error_fragment in result.out


def test_missing_script_file(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": _tox_ini()})
    result = proj.run("r", "-e", "check", "--discover", sys.executable)
    result.assert_failed()
    assert "script file not found" in result.out


def test_base_python_rejected(tox_project: ToxProjectCreator) -> None:
    script = f'# /// script\n# requires-python = ">={_py_ver()}"\n# ///\n'
    result, _ = _run(
        tox_project,
        {"tox.ini": _tox_ini("base_python = python3"), "check.py": script},
    )
    result.assert_failed()
    assert "cannot set base_python" in result.out


def _tox_ini_with_script(script_value: str) -> str:
    return f"[testenv:check]\nrunner = virtualenv-pep-723\nscript = {script_value}\n"


def test_script_path_outside_tox_root_rejected(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": _tox_ini_with_script("../escape.py")})
    result = proj.run("r", "-e", "check", "--discover", sys.executable)
    result.assert_failed()
    assert "escapes tox_root" in result.out


def test_script_path_traversal_via_dot_dot_rejected(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": _tox_ini_with_script("subdir/../../etc/passwd")})
    result = proj.run("r", "-e", "check", "--discover", sys.executable)
    result.assert_failed()
    assert "escapes tox_root" in result.out


def test_script_file_too_large_rejected(tox_project: ToxProjectCreator, mocker: MockerFixture) -> None:
    script = "# /// script\n# dependencies = []\n# ///\nprint('ok')\n"
    proj = tox_project({"tox.ini": _tox_ini(), "check.py": script})
    proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    mocker.patch("tox.tox_env.python.pep723._MAX_SCRIPT_BYTES", 1)
    result = proj.run("r", "-e", "check", "--discover", sys.executable)
    result.assert_failed()
    assert "exceeds the 1 byte limit" in result.out
