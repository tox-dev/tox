import os
from pathlib import Path
from typing import Tuple

import pytest
from pytest_mock import MockerFixture
from virtualenv import __version__ as virtualenv_version
from virtualenv import session_via_cli
from virtualenv.config.cli.parser import VirtualEnvOptions

from tox.execute import ExecuteRequest
from tox.pytest import MonkeyPatch, ToxProject, ToxProjectCreator


@pytest.fixture()
def virtualenv_opt(monkeypatch: MonkeyPatch, mocker: MockerFixture) -> VirtualEnvOptions:
    for key in os.environ:
        if key.startswith("VIRTUALENV_"):  # pragma: no cover
            monkeypatch.delenv(key)  # pragma: no cover
    opts = VirtualEnvOptions()
    mocker.patch(
        "tox.tox_env.python.virtual_env.api.session_via_cli",
        side_effect=lambda args, options, setup_logging, env: session_via_cli(args, opts, setup_logging, env),
    )
    return opts


def test_virtualenv_default_settings(tox_project: ToxProjectCreator, virtualenv_opt: VirtualEnvOptions) -> None:
    proj = tox_project({"tox.ini": "[testenv]\npackage=skip"})
    result = proj.run("r", "-e", "py")
    result.assert_success()

    conf = result.env_conf("py")
    assert conf["system_site_packages"] is False
    assert conf["always_copy"] is False
    assert conf["download"] is False

    assert virtualenv_opt.clear is False
    assert virtualenv_opt.system_site is False
    assert virtualenv_opt.download is False
    assert virtualenv_opt.copies is False
    assert virtualenv_opt.no_periodic_update is True
    assert virtualenv_opt.python == ["py"]


def test_virtualenv_flipped_settings(
    tox_project: ToxProjectCreator, virtualenv_opt: VirtualEnvOptions, monkeypatch: MonkeyPatch
) -> None:
    proj = tox_project(
        {"tox.ini": "[testenv]\npackage=skip\nsystem_site_packages=True\nalways_copy=True\ndownload=True"}
    )
    monkeypatch.setenv("VIRTUALENV_CLEAR", "0")

    result = proj.run("r", "-e", "py")
    result.assert_success()

    conf = result.env_conf("py")
    assert conf["system_site_packages"] is True
    assert conf["always_copy"] is True
    assert conf["download"] is True

    assert virtualenv_opt.clear is False
    assert virtualenv_opt.system_site is True
    assert virtualenv_opt.download is True
    assert virtualenv_opt.copies is True
    assert virtualenv_opt.python == ["py"]


def test_virtualenv_env_ignored_if_set(
    tox_project: ToxProjectCreator, virtualenv_opt: VirtualEnvOptions, monkeypatch: MonkeyPatch
) -> None:
    ini = "[testenv]\npackage=skip\nsystem_site_packages=True\nalways_copy=True\ndownload=True"
    proj = tox_project({"tox.ini": ini})
    monkeypatch.setenv("VIRTUALENV_COPIES", "0")
    monkeypatch.setenv("VIRTUALENV_DOWNLOAD", "0")
    monkeypatch.setenv("VIRTUALENV_SYSTEM_SITE_PACKAGES", "0")
    run_and_check_set(proj, virtualenv_opt)


def test_virtualenv_env_used_if_not_set(
    tox_project: ToxProjectCreator, virtualenv_opt: VirtualEnvOptions, monkeypatch: MonkeyPatch
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
    assert virtualenv_opt.copies is True


def test_honor_set_env_for_clear_periodic_update(
    tox_project: ToxProjectCreator, virtualenv_opt: VirtualEnvOptions
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

    from tox.tox_env.python.virtual_env import api

    mocker.patch.object(api, "virtualenv_version", "1.0")
    result = proj.run("r")
    assert f"recreate env because python changed virtualenv version='1.0'->'{virtualenv_version}'" in result.out
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


def test_install_command_no_packages(tox_project: ToxProjectCreator, disable_pip_pypi_access: Tuple[str, str]) -> None:
    install_cmd = "python -m pip install -i {env:PIP_INDEX_URL}"
    proj = tox_project({"tox.ini": f"[testenv]\npackage=skip\ninstall_command={install_cmd}\npip_pre=true\ndeps=magic"})
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("r")
    result.assert_success()
    request: ExecuteRequest = execute_calls.call_args[0][3]
    found_cmd = request.cmd
    assert found_cmd == ["python", "-m", "pip", "install", "-i", disable_pip_pypi_access[0], "--pre", "magic"]


def test_list_dependencies_command(tox_project: ToxProjectCreator) -> None:
    install_cmd = "python -m pip freeze"
    proj = tox_project({"tox.ini": f"[testenv]\npackage=skip\nlist_dependencies_command={install_cmd}"})
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("r", "--result-json", str(proj.path / "out.json"))
    result.assert_success()
    request: ExecuteRequest = execute_calls.call_args[0][3]
    assert request.cmd == ["python", "-m", "pip", "freeze"]


@pytest.mark.parametrize("mode", ["r", "p", "le"])
def test_install_pkg(tox_project: ToxProjectCreator, mode: str) -> None:
    proj = tox_project({"tox.ini": "[testenv]\npackage=wheel"})
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    file = proj.path / "a"
    file.write_text("")

    result = proj.run(mode, "--installpkg", str(file))

    result.assert_success()
    execute_calls.assert_called_once()
    request: ExecuteRequest = execute_calls.call_args[0][3]
    assert request.cmd == ["python", "-I", "-m", "pip", "install", str(file)]


def test_can_build_and_run_python_2(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    try:
        session_via_cli(["-p", "2.7", "venv"])
    except RuntimeError:  # pragma: no cover
        pytest.skip("no python 2.7 interpreter")  # pragma: no cover
    proj = tox_project({"tox.ini": "[testenv]\npackage=wheel"})
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("r", "-e", "py27", "--root", str(demo_pkg_inline))
    result.assert_success()

    install_cmd = next(
        i[0][3].cmd for i in execute_calls.call_args_list if "install" in i[0][3].run_id
    )  # pragma: no cover
    assert install_cmd[:-1] == ["python", "-E", "-m", "pip", "install", "--force-reinstall", "--no-deps"]
