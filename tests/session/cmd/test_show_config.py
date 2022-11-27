from __future__ import annotations

import platform
import sys
from configparser import ConfigParser
from pathlib import Path
from textwrap import dedent
from typing import Callable

import pytest
from pytest_mock import MockerFixture

from tox.config.types import Command
from tox.pytest import MonkeyPatch, ToxProjectCreator


def test_show_config_default_run_env(tox_project: ToxProjectCreator, monkeypatch: MonkeyPatch) -> None:
    py_ver = sys.version_info[0:2]
    name = f"py{py_ver[0]}{py_ver[1]}" if platform.python_implementation() == "CPython" else "pypy3"
    project = tox_project({"tox.ini": f"[tox]\nenv_list = {name}\n[testenv:{name}]\ncommands={{posargs}}"})
    result = project.run("c", "-e", name, "--core", "--", "magic")
    state = result.state
    assert state.args == ("c", "-e", name, "--core", "--", "magic")
    outcome = list(state.envs.iter(only_active=False))
    assert outcome == [name]
    monkeypatch.delenv("TERM", raising=False)  # disable conditionally set flag
    parser = ConfigParser(interpolation=None)
    parser.read_string(result.out)
    assert list(parser.sections()) == [f"testenv:{name}", "tox"]


def test_show_config_commands(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.ini": """
        [tox]
        env_list = py
        no_package = true
        [testenv]
        commands_pre =
            python -c 'import sys; print("start", sys.executable)'
        commands =
            pip config list
            pip list
        commands_post =
            python -c 'import sys; print("end", sys.executable)'
        """,
        },
    )
    outcome = project.run("c")
    outcome.assert_success()
    env_config = outcome.env_conf("py")
    assert env_config["commands_pre"] == [Command(args=["python", "-c", 'import sys; print("start", sys.executable)'])]
    assert env_config["commands"] == [
        Command(args=["pip", "config", "list"]),
        Command(args=["pip", "list"]),
    ]
    assert env_config["commands_post"] == [Command(args=["python", "-c", 'import sys; print("end", sys.executable)'])]


def test_show_config_filter_keys(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[testenv]\nmagic=yes"})
    outcome = project.run("c", "-e", "py", "-k", "no_package", "env_name", "--core")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:py]\nenv_name = py\n\n[tox]\nno_package = False\n", "")


def test_show_config_unused(tox_project: ToxProjectCreator) -> None:
    tox_ini = "[testenv]\nok=false\n[testenv:py]\nmagical=yes\nmagic=yes"
    outcome = tox_project({"tox.ini": tox_ini}).run("c", "-e", "py")
    outcome.assert_success()
    assert "\n# !!! unused: magic, magical\n" in outcome.out


def test_show_config_exception(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.ini": """
        [testenv:a]
        base_python = missing-python
        """,
        },
    )
    outcome = project.run("c", "-e", "a", "-k", "env_site_packages_dir")
    outcome.assert_success()
    txt = (
        "\nenv_site_packages_dir = # Exception: "
        "RuntimeError(\"failed to find interpreter for Builtin discover of python_spec='missing-python'"
    )
    assert txt in outcome.out


@pytest.mark.parametrize("stdout_is_atty", [True, False])
def test_pass_env_config_default(tox_project: ToxProjectCreator, stdout_is_atty: bool, mocker: MockerFixture) -> None:
    mocker.patch("sys.stdout.isatty", return_value=stdout_is_atty)
    project = tox_project({"tox.ini": ""})
    outcome = project.run("c", "-e", "py", "-k", "pass_env")
    pass_env = outcome.env_conf("py")["pass_env"]
    is_win = sys.platform == "win32"
    expected = (
        (["COMSPEC"] if is_win else [])
        + ["CURL_CA_BUNDLE", "LANG", "LANGUAGE", "LD_LIBRARY_PATH"]
        + (["MSYSTEM", "PATHEXT"] if is_win else [])
        + ["PIP_*"]
        + (["PROCESSOR_ARCHITECTURE"] if is_win else [])
        + (["PROGRAMDATA"] if is_win else [])
        + (["PROGRAMFILES"] if is_win else [])
        + (["PROGRAMFILES(x86)"] if is_win else [])
        + ["REQUESTS_CA_BUNDLE", "SSL_CERT_FILE"]
        + (["SYSTEMDRIVE", "SYSTEMROOT", "TEMP"] if is_win else [])
        + (["TERM"] if stdout_is_atty else [])
        + (["TMP", "USERPROFILE"] if is_win else ["TMPDIR"])
        + ["VIRTUALENV_*", "http_proxy", "https_proxy", "no_proxy"]
    )
    assert pass_env == expected


def test_show_config_pkg_env_once(
    tox_project: ToxProjectCreator,
    patch_prev_py: Callable[[bool], tuple[str, str]],
) -> None:
    prev_ver, impl = patch_prev_py(True)
    project = tox_project(
        {"tox.ini": f"[tox]\nenv_list=py{prev_ver},py\n[testenv]\npackage=wheel", "pyproject.toml": ""},
    )
    result = project.run("c")
    result.assert_success()
    parser = ConfigParser(interpolation=None)
    parser.read_string(result.out)
    sections = set(parser.sections())
    assert sections == {"testenv:.pkg", f"testenv:.pkg-{impl}{prev_ver}", f"testenv:py{prev_ver}", "testenv:py", "tox"}


def test_show_config_pkg_env_skip(
    tox_project: ToxProjectCreator,
    patch_prev_py: Callable[[bool], tuple[str, str]],
) -> None:
    prev_ver, impl = patch_prev_py(False)
    project = tox_project(
        {"tox.ini": f"[tox]\nenv_list=py{prev_ver},py\n[testenv]\npackage=wheel", "pyproject.toml": ""},
    )
    result = project.run("c")
    result.assert_success()
    parser = ConfigParser(interpolation=None)
    parser.read_string(result.out)
    sections = set(parser.sections())
    assert sections == {"testenv:.pkg", "tox", "testenv:py", f"testenv:py{prev_ver}"}


def test_show_config_select_only(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[tox]\nenv_list=\n a\n b", "pyproject.toml": ""})
    result = project.run("c", "-e", ".pkg,b,.pkg")
    result.assert_success()
    parser = ConfigParser(interpolation=None)
    parser.read_string(result.out)
    sections = list(parser.sections())
    assert sections == ["testenv:.pkg", "testenv:b"]


def test_show_config_alias(tox_project: ToxProjectCreator) -> None:
    outcome = tox_project({"tox.ini": ""}).run("c", "-e", "py", "-k", "setenv")
    outcome.assert_success()
    assert "set_env = " in outcome.out


def test_show_config_description_normalize(tox_project: ToxProjectCreator) -> None:
    tox_ini = "[testenv]\ndescription = A   magical\t pipe\n  of\tthis"
    outcome = tox_project({"tox.ini": tox_ini}).run("c", "-e", "py", "-k", "description")
    outcome.assert_success()
    assert outcome.out == "[testenv:py]\ndescription = A magical pipe of this\n"


def test_show_config_ini_comment_path(tox_project: ToxProjectCreator, tmp_path: Path) -> None:
    prj_path = tmp_path / "#magic"
    prj_path.mkdir()
    ini = """
    [testenv]
    package = skip
    set_env =
        A=1 # comment
        # more comment
    commands = {envpython} -c 'import os; print(os.linesep.join(f"{k}={v}" for k, v in os.environ.items()))'
    [testenv:py]
    set_env =
        {[testenv]set_env}
        B = {tox_root} # just some comment
    """
    project = tox_project({"tox.ini": dedent(ini)}, prj_path=prj_path)
    result = project.run("r", "-e", "py")
    result.assert_success()
    a_line = next(i for i in result.out.splitlines() if i.startswith("A="))  # pragma: no branch  # not found raises
    assert a_line == "A=1"
    b_line = next(i for i in result.out.splitlines() if i.startswith("B="))  # pragma: no branch  # not found raises
    assert b_line == f"B={prj_path}"


def test_show_config_cli_flag(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "", "pyproject.toml": ""})
    result = project.run("c", "-e", "py,.pkg", "-k", "package", "recreate", "--develop", "-r", "--no-recreate-pkg")
    expected = "[testenv:py]\npackage = editable\nrecreate = True\n\n[testenv:.pkg]\nrecreate = False\n"
    assert result.out == expected


def test_show_config_timeout_default(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[testenv]\npakcage=skip"})
    result = project.run("c", "-e", "py", "-k", "suicide_timeout", "interrupt_timeout", "terminate_timeout")
    expected = "[testenv:py]\nsuicide_timeout = 0.0\ninterrupt_timeout = 0.3\nterminate_timeout = 0.2\n"
    assert result.out == expected


def test_show_config_timeout_custom(tox_project: ToxProjectCreator) -> None:
    ini = "[testenv]\npakcage=skip\nsuicide_timeout = 1\ninterrupt_timeout = 2.222\nterminate_timeout = 3.0\n"
    project = tox_project({"tox.ini": ini})
    result = project.run("c", "-e", "py", "-k", "suicide_timeout", "interrupt_timeout", "terminate_timeout")
    expected = "[testenv:py]\nsuicide_timeout = 1.0\ninterrupt_timeout = 2.222\nterminate_timeout = 3.0\n"
    assert result.out == expected


def test_show_config_help(tox_project: ToxProjectCreator) -> None:
    outcome = tox_project({"tox.ini": ""}).run("c", "-h")
    outcome.assert_success()
