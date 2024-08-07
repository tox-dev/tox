from __future__ import annotations

import platform
import sys
from configparser import ConfigParser
from textwrap import dedent
from typing import TYPE_CHECKING, Callable

import pytest

from tox.config.types import Command

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

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


def test_show_config_py_ver_impl_constants(tox_project: ToxProjectCreator) -> None:
    tox_ini = "[testenv]\npackage=skip\ndeps= {py_impl}{py_dot_ver}"
    outcome = tox_project({"tox.ini": tox_ini}).run("c", "-e", "py", "-k", "py_dot_ver", "py_impl", "deps")
    outcome.assert_success()
    py_ver = ".".join(str(i) for i in sys.version_info[0:2])
    impl = sys.implementation.name
    assert outcome.out == f"[testenv:py]\npy_dot_ver = {py_ver}\npy_impl = {impl}\ndeps = {impl}{py_ver}\n"


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


def test_show_config_empty_install_command_exception(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[testenv:a]\ninstall_command="})
    outcome = project.run("c", "-e", "a", "-k", "install_command")
    outcome.assert_success()
    txt = "\ninstall_command = # Exception: ValueError(\"attempting to parse '' into a command failed\")"
    assert txt in outcome.out


@pytest.mark.parametrize("stdout_is_atty", [True, False])
def test_pass_env_config_default(tox_project: ToxProjectCreator, stdout_is_atty: bool, mocker: MockerFixture) -> None:
    mocker.patch("sys.stdout.isatty", return_value=stdout_is_atty)
    project = tox_project({"tox.ini": ""})
    outcome = project.run("c", "-e", "py", "-k", "pass_env")
    pass_env = outcome.env_conf("py")["pass_env"]
    is_win = sys.platform == "win32"
    expected = (
        []
        + (["APPDATA"] if is_win else [])
        + ["CC", "CCSHARED", "CFLAGS"]
        + (["COMSPEC"] if is_win else [])
        + ["CPPFLAGS", "CURL_CA_BUNDLE", "CXX", "FORCE_COLOR", "HOME", "LANG"]
        + ["LANGUAGE", "LDFLAGS", "LD_LIBRARY_PATH"]
        + (["MSYSTEM"] if is_win else [])
        + ["NO_COLOR"]
        + (["NUMBER_OF_PROCESSORS", "PATHEXT"] if is_win else [])
        + ["PIP_*", "PKG_CONFIG", "PKG_CONFIG_PATH", "PKG_CONFIG_SYSROOT_DIR"]
        + (["PROCESSOR_ARCHITECTURE"] if is_win else [])
        + (["PROGRAMDATA"] if is_win else [])
        + (["PROGRAMFILES"] if is_win else [])
        + (["PROGRAMFILES(x86)"] if is_win else [])
        + ["REQUESTS_CA_BUNDLE", "SSL_CERT_FILE"]
        + (["SYSTEMDRIVE", "SYSTEMROOT", "TEMP"] if is_win else [])
        + (["TERM"] if stdout_is_atty else [])
        + (["TMP", "USERPROFILE"] if is_win else ["TMPDIR"])
        + ["VIRTUALENV_*"]
        + (["WINDIR"] if is_win else [])
        + ["http_proxy", "https_proxy", "no_proxy"]
    )
    assert pass_env == expected


def test_show_config_pkg_env_once(
    tox_project: ToxProjectCreator,
    patch_prev_py: Callable[[bool], tuple[str, str]],
) -> None:
    prev_ver, impl = patch_prev_py(True)
    ini = f"[tox]\nenv_list=py{prev_ver},py\n[testenv]\npackage=wheel"
    project = tox_project({"tox.ini": ini, "pyproject.toml": ""})
    result = project.run("c", "-e", "ALL")
    result.assert_success()
    parser = ConfigParser(interpolation=None)
    parser.read_string(result.out)
    sections = set(parser.sections())
    assert sections == {"testenv:.pkg", f"testenv:.pkg-{impl}{prev_ver}", f"testenv:py{prev_ver}", "testenv:py", "tox"}


def test_show_config_pkg_env_skip(
    tox_project: ToxProjectCreator,
    patch_prev_py: Callable[[bool], tuple[str, str]],
) -> None:
    prev_ver, _impl = patch_prev_py(False)
    ini = f"[tox]\nenv_list=py{prev_ver},py\n[testenv]\npackage=wheel"
    project = tox_project({"tox.ini": ini, "pyproject.toml": ""})
    result = project.run("c", "-e", "ALL")
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
    assert "set_env =" in outcome.out


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


def test_show_config_core_host_python(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": ""})
    outcome = project.run("c", "--core", "-e", "py", "-k", "host_python")
    outcome.assert_success()
    assert f"host_python = {sys.executable}" in outcome.out


def test_show_config_matching_env_section(tox_project: ToxProjectCreator) -> None:
    ini = """
    [a]
    [testenv:a]
    deps = c>=1
    [testenv:b]
    deps = {[testenv:a]deps}"""
    project = tox_project({"tox.ini": ini})
    outcome = project.run("c", "-e", "a,b", "-k", "deps")
    outcome.assert_success()
    assert outcome.out.count("c>=1") == 2, outcome.out


def test_package_env_inherits_from_pkgenv(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    project = tox_project({"tox.ini": "[pkgenv]\npass_env = A, AA\ndeps=C\n D"})
    outcome = project.run("c", "--root", str(demo_pkg_inline), "-k", "deps", "pass_env", "-e", "py,.pkg")
    outcome.assert_success()
    exp = """
    [testenv:.pkg]
    deps =
      C
      D
    pass_env =
      A
      AA
    """
    exp = dedent(exp)
    assert exp in outcome.out


def test_core_on_platform(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[tox]\nno_package = true"})
    result = project.run("c", "-e", "py", "--core", "-k", "on_platform")
    result.assert_success()
    assert result.out == f"[testenv:py]\n\n[tox]\non_platform = {sys.platform}\n"
