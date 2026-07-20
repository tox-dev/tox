from __future__ import annotations

import os
import sys
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, PropertyMock

import pytest
from virtualenv import __version__ as virtualenv_version
from virtualenv import session_via_cli
from virtualenv.config.cli.parser import VirtualEnvOptions

from tox.tox_env.python.virtual_env.api import VirtualEnv

if TYPE_CHECKING:
    from collections.abc import Callable

    from pytest_mock import MockerFixture

    from tox.execute import ExecuteRequest
    from tox.pytest import MonkeyPatch, ToxProject, ToxProjectCreator


@pytest.fixture
def virtualenv_opt(monkeypatch: MonkeyPatch, mocker: MockerFixture) -> VirtualEnvOptions:
    for key in os.environ:
        if key.startswith("VIRTUALENV_"):  # pragma: no cover
            monkeypatch.delenv(key)  # pragma: no cover
    opts = VirtualEnvOptions()
    mocker.patch(
        "tox.tox_env.python.virtual_env.api.session_via_cli",
        side_effect=lambda args, options, setup_logging, env: session_via_cli(  # ruff:ignore[unused-lambda-argument]
            args,
            opts,
            setup_logging,
            env,
        ),
    )
    return opts


def test_virtualenv_default_settings(tox_project: ToxProjectCreator, virtualenv_opt: VirtualEnvOptions) -> None:
    proj = tox_project({"tox.ini": "[testenv]\npackage=skip"})
    result = proj.run("r", "-e", "py3", "--discover", sys.executable, str(proj.path / "a"))
    result.assert_success()

    conf = result.env_conf("py3")
    assert conf["system_site_packages"] is False
    assert conf["always_copy"] is False
    assert conf["download"] is False

    assert virtualenv_opt.clear is False
    assert virtualenv_opt.system_site is False
    assert virtualenv_opt.download is False
    if hasattr(virtualenv_opt, "copies"):
        assert virtualenv_opt.copies is False
    assert virtualenv_opt.no_periodic_update is True
    assert virtualenv_opt.python == ["py3"]
    assert virtualenv_opt.try_first_with == [str(sys.executable), str(proj.path / "a")]


def test_virtualenv_flipped_settings(
    tox_project: ToxProjectCreator,
    virtualenv_opt: VirtualEnvOptions,
    monkeypatch: MonkeyPatch,
) -> None:
    proj = tox_project(
        {"tox.ini": "[testenv]\npackage=skip\nsystem_site_packages=True\nalways_copy=True\ndownload=True"},
    )
    monkeypatch.setenv("VIRTUALENV_CLEAR", "0")

    result = proj.run("r", "-e", "py3")
    result.assert_success()

    conf = result.env_conf("py3")
    assert conf["system_site_packages"] is True
    assert conf["always_copy"] is True
    assert conf["download"] is True

    assert virtualenv_opt.clear is False
    assert virtualenv_opt.system_site is True
    assert virtualenv_opt.download is True
    if hasattr(virtualenv_opt, "copies"):
        assert virtualenv_opt.copies is True
    assert virtualenv_opt.python == ["py3"]


def test_virtualenv_env_ignored_if_set(
    tox_project: ToxProjectCreator,
    virtualenv_opt: VirtualEnvOptions,
    monkeypatch: MonkeyPatch,
) -> None:
    ini = "[testenv]\npackage=skip\nsystem_site_packages=True\nalways_copy=True\ndownload=True"
    proj = tox_project({"tox.ini": ini})
    monkeypatch.setenv("VIRTUALENV_COPIES", "0")
    monkeypatch.setenv("VIRTUALENV_DOWNLOAD", "0")
    monkeypatch.setenv("VIRTUALENV_SYSTEM_SITE_PACKAGES", "0")
    run_and_check_set(proj, virtualenv_opt)


def test_virtualenv_env_used_if_not_set(
    tox_project: ToxProjectCreator,
    virtualenv_opt: VirtualEnvOptions,
    monkeypatch: MonkeyPatch,
) -> None:
    proj = tox_project({"tox.ini": "[testenv]\npackage=skip"})
    monkeypatch.setenv("VIRTUALENV_COPIES", "1")
    monkeypatch.setenv("VIRTUALENV_DOWNLOAD", "1")
    monkeypatch.setenv("VIRTUALENV_SYSTEM_SITE_PACKAGES", "1")
    run_and_check_set(proj, virtualenv_opt)


def run_and_check_set(proj: ToxProject, virtualenv_opt: VirtualEnvOptions) -> None:
    result = proj.run("r", "-e", "py")
    result.assert_success()
    conf = result.env_conf("py")
    assert conf["system_site_packages"] is True
    assert conf["always_copy"] is True
    assert conf["download"] is True
    assert virtualenv_opt.system_site is True
    assert virtualenv_opt.download is True
    if hasattr(virtualenv_opt, "copies"):
        assert virtualenv_opt.copies is True


def test_honor_set_env_for_clear_periodic_update(
    tox_project: ToxProjectCreator,
    virtualenv_opt: VirtualEnvOptions,
) -> None:
    ini = "[testenv]\npackage=skip\nset_env=\n  VIRTUALENV_CLEAR=0\n  VIRTUALENV_NO_PERIODIC_UPDATE=0"
    proj = tox_project({"tox.ini": ini})
    result = proj.run("r", "-e", "py")
    result.assert_success()

    assert virtualenv_opt.clear is False
    assert virtualenv_opt.no_periodic_update is False


def test_recreate_when_virtualenv_changes(tox_project: ToxProjectCreator, mocker: MockerFixture) -> None:
    proj = tox_project({"tox.ini": "[testenv]\npackage=skip"})
    proj.run("r")

    from tox.tox_env.python.virtual_env import api  # ruff:ignore[import-outside-top-level]

    mocker.patch.object(api, "virtualenv_version", "1.0")
    result = proj.run("r")
    assert f"recreate env because python changed virtualenv version='{virtualenv_version}'->'1.0'" in result.out
    assert "remove tox env folder" in result.out


@pytest.mark.parametrize("on", [True, False])
def test_pip_pre(tox_project: ToxProjectCreator, on: bool) -> None:
    proj = tox_project({"tox.ini": f"[testenv]\npackage=skip\npip_pre={on}\ndeps=magic"})
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("r", "-e", "py")
    result.assert_success()
    if on:
        assert "--pre" in execute_calls.call_args[0][3].cmd
    else:
        assert "--pre" not in execute_calls.call_args[0][3].cmd


def test_install_command_no_packages(tox_project: ToxProjectCreator, disable_pip_pypi_access: tuple[str, str]) -> None:
    install_cmd = "python -m pip install -i {env:PIP_INDEX_URL}"
    proj = tox_project({"tox.ini": f"[testenv]\npackage=skip\ninstall_command={install_cmd}\npip_pre=true\ndeps=magic"})
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("r")
    result.assert_success()
    request: ExecuteRequest = execute_calls.call_args[0][3]
    found_cmd = request.cmd
    assert found_cmd == ["python", "-m", "pip", "install", "-i", disable_pip_pypi_access[0], "--pre", "magic"]


@pytest.mark.slow
def test_list_dependencies_command(tox_project: ToxProjectCreator) -> None:
    install_cmd = "python -m pip freeze"
    proj = tox_project({"tox.ini": f"[testenv]\npackage=skip\nlist_dependencies_command={install_cmd}"})
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("r", "--result-json", str(proj.path / "out.json"))
    result.assert_success()
    request: ExecuteRequest = execute_calls.call_args[0][3]
    assert request.cmd == ["python", "-m", "pip", "freeze"]


def test_posargs_colon_in_inactive_env_does_not_crash(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.toml": """
            env_list = ["hello"]

            [env.hello]
            package = "skip"
            commands = [["python", "-c", "print('ok')"]]

            [env.dev]
            env_dir = "{posargs:venv}"
            package = "editable"
            commands = [["python", "-c", "print('dev')"]]
        """,
    })
    outcome = project.run("r", "-e", "hello", "--", "x:y")
    outcome.assert_success()
    assert "ok" in outcome.out


def test_env_site_packages_dir_plat(tox_project: ToxProjectCreator) -> None:
    toml = """\
[env_run_base]
package = "skip"
commands = [["python", "-c", "print('ok')"]]
"""
    result = tox_project({"tox.toml": toml}).run("c", "-e", "py", "-k", "env_site_packages_dir_plat")
    result.assert_success()
    assert "site-packages" in result.out


def test_pip_user_disabled(tox_project: ToxProjectCreator) -> None:
    proj = tox_project(
        {
            "tox.toml": """
                [env_run_base]
                package = "skip"
                commands = [
                    ["python", "-c", "import os; print('PIP_USER=' + os.environ.get('PIP_USER', 'NOT_SET'))"]
                ]
            """,
        },
    )
    result = proj.run("r", "-e", "py")
    result.assert_success()
    assert "PIP_USER=0" in result.out


@pytest.mark.parametrize(
    ("var", "substitution", "expected_fragment"),
    [
        pytest.param("COVERAGE_SRC", "{env_site_packages_dir}", "site-packages", id="env_site_packages_dir"),
        pytest.param("MY_BIN", "{env_bin_dir}", "Scripts" if sys.platform == "win32" else "bin", id="env_bin_dir"),
        pytest.param("MY_PYTHON", "{env_python}", "python", id="env_python"),
    ],
)
def test_set_env_lazy_constant_no_circular_dependency(
    tox_project: ToxProjectCreator,
    var: str,
    substitution: str,
    expected_fragment: str,
) -> None:
    proj = tox_project(
        {
            "tox.toml": f"""\
[env_run_base]
package = "skip"
set_env.{var} = "{substitution}"
commands = [["python", "-c", "print('ok')"]]
""",
        },
    )
    result = proj.run("c", "-e", "py", "-k", "set_env")
    result.assert_success()
    assert f"{var}=" in result.out
    assert expected_fragment in result.out


def test_get_python_returns_none_when_system_executable_missing(
    tox_project: ToxProjectCreator,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        VirtualEnv,
        "creator",
        new_callable=PropertyMock,
        return_value=MagicMock(interpreter=MagicMock(system_executable=None)),
    )
    proj = tox_project({"tox.ini": "[testenv]\npackage=skip\nbase_python=missing-interp"})
    result = proj.run("r")
    result.assert_failed()
    assert "could not find python interpreter" in result.out


def test_get_virtualenv_py_info_raises_on_none(mocker: MockerFixture) -> None:
    mocker.patch("virtualenv.discovery.cached_py_info.from_exe", return_value=None)
    with pytest.raises(RuntimeError, match="could not query python information for"):
        VirtualEnv.get_virtualenv_py_info(Path("/no/such/python"))


@pytest.fixture
def resolve_virtualenv_spec(
    tox_project: ToxProjectCreator,
    mocker: MockerFixture,
) -> Callable[[list[str], str], str]:
    def _resolve(base_pythons: list[str], installed: str) -> str:
        mocker.patch("tox.tox_env.python.virtual_env.api.virtualenv_version", installed)
        candidates = ", ".join(f'"{base_python}"' for base_python in base_pythons)
        proj = tox_project({
            "tox.toml": dedent(
                f"""\
                [env.foo]
                package = "skip"
                base_python = [{candidates}]
                commands = [["python", "-c", "print(1)"]]
                """,
            ),
        })
        result = proj.run("c", "-e", "foo", "-k", "virtualenv_spec")
        result.assert_success()
        line = next(ln for ln in result.out.splitlines() if ln.strip().startswith("virtualenv_spec ="))
        return line.split("=", 1)[1].strip()

    return _resolve


@pytest.mark.parametrize(
    ("base_pythons", "installed", "expected"),
    [
        pytest.param(["py38"], "21.5.1", "virtualenv<21.5.0", id="py38-new-virtualenv-pins"),
        pytest.param(["py38"], "20.26.0", "", id="py38-old-virtualenv-already-works"),
        pytest.param(["py37"], "21.5.1", "virtualenv<21.5.0", id="py37-new-virtualenv-pins"),
        pytest.param(["py39"], "21.5.1", "", id="py39-supported"),
        pytest.param(["py313"], "21.5.1", "", id="py313-supported"),
        pytest.param(["py38", "py39"], "21.5.1", "", id="mixed-one-supported-no-pin"),
        pytest.param(["py38", "py37"], "21.5.1", "virtualenv<21.5.0", id="all-unsupported-pins"),
        pytest.param(["py38", "py36"], "21.5.1", "virtualenv<20.22.0", id="most-restrictive-floor"),
        pytest.param(["py36"], "20.26.0", "virtualenv<20.22.0", id="py36-needs-older-virtualenv"),
        pytest.param(["py36"], "20.21.0", "", id="py36-old-virtualenv-already-works"),
        pytest.param(["py3"], "21.5.1", "", id="underspecified-minor-unknown"),
        pytest.param(["/usr/bin/python3.8"], "21.5.1", "", id="bare-path-version-unknown"),
        pytest.param(["python3.8"], "21.5.1", "virtualenv<21.5.0", id="command-form-pins"),
        pytest.param([], "21.5.1", "", id="no-candidates"),
    ],
)
def test_virtualenv_spec_auto(
    resolve_virtualenv_spec: Callable[[list[str], str], str],
    base_pythons: list[str],
    installed: str,
    expected: str,
) -> None:
    assert resolve_virtualenv_spec(base_pythons, installed) == expected


@pytest.mark.parametrize(
    "resolves",
    [
        pytest.param(False, id="interpreter-unresolved"),
        pytest.param(True, id="resolved-but-probe-fails"),
    ],
)
def test_virtualenv_spec_subprocess_missing_interpreter(
    tox_project: ToxProjectCreator,
    mocker: MockerFixture,
    resolves: bool,
) -> None:
    ensure_bootstrap = mocker.patch(
        "tox.tox_env.python.virtual_env.subprocess_adapter.ensure_bootstrap",
        return_value=Path(sys.executable),
    )
    resolved = MagicMock(system_executable=sys.executable) if resolves else None
    mocker.patch("tox.tox_env.python.virtual_env.api.get_interpreter", return_value=resolved)
    mocker.patch("tox.tox_env.python.virtual_env.subprocess_adapter.probe_python", return_value=None)
    proj = tox_project({
        "tox.toml": dedent(
            """\
            [env_run_base]
            package = "skip"
            virtualenv_spec = "virtualenv<20.22.0"
            """,
        ),
    })
    result = proj.run("r", "-e", "py")
    result.assert_failed()
    assert "could not find python interpreter" in result.out
    ensure_bootstrap.assert_not_called()  # a missing interpreter must skip without bootstrapping
