import platform
import sys
from configparser import ConfigParser
from typing import Callable, Tuple

import pytest
from pytest_mock import MockerFixture

from tox.config.types import Command
from tox.pytest import MonkeyPatch, ToxProjectCreator


def test_show_config_default_run_env(tox_project: ToxProjectCreator, monkeypatch: MonkeyPatch) -> None:
    py_ver = sys.version_info[0:2]
    name = "py{}{}".format(*py_ver) if platform.python_implementation() == "CPython" else "pypy3"
    project = tox_project({"tox.ini": f"[tox]\nenv_list = {name}\n[testenv:{name}]\ncommands={{posargs}}"})
    result = project.run("c", "-e", name, "--core", "--", "magic")
    state = result.state
    assert state.args == ("c", "-e", name, "--core", "--", "magic")
    outcome = list(state.env_list(everything=True))
    assert outcome == [name]
    monkeypatch.delenv("TERM", raising=False)  # disable conditionally set flag
    parser = ConfigParser()
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
    env_config = outcome.state.tox_env("py").conf
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
    outcome = tox_project({"tox.ini": "[testenv:py]\nmagical=yes\nmagic=yes"}).run("c", "-e", "py")
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
    pass_env = outcome.state.tox_env("py").conf["pass_env"]
    is_win = sys.platform == "win32"
    expected = (
        (["COMSPEC"] if is_win else [])
        + ["CURL_CA_BUNDLE", "LANG", "LANGUAGE", "LD_LIBRARY_PATH"]
        + (["MSYSTEM", "PATHEXT"] if is_win else [])
        + ["PIP_*"]
        + (["PROCESSOR_ARCHITECTURE"] if is_win else [])
        + ["REQUESTS_CA_BUNDLE", "SSL_CERT_FILE"]
        + (["SYSTEMDRIVE", "SYSTEMROOT", "TEMP"] if is_win else [])
        + (["TERM"] if stdout_is_atty else [])
        + (["TMP", "USERPROFILE"] if is_win else ["TMPDIR"])
        + ["VIRTUALENV_*", "http_proxy", "https_proxy", "no_proxy"]
    )
    assert pass_env == expected


def test_show_config_pkg_env_once(
    tox_project: ToxProjectCreator, patch_prev_py: Callable[[bool], Tuple[str, str]]
) -> None:
    prev_ver, impl = patch_prev_py(True)
    project = tox_project({"tox.ini": f"[tox]\nenv_list=py{prev_ver},py\n[testenv]\npackage=wheel"})
    result = project.run("c")
    result.assert_success()
    parser = ConfigParser()
    parser.read_string(result.out)
    sections = set(parser.sections())
    assert sections == {"testenv:.pkg", f"testenv:.pkg-{impl}{prev_ver}", f"testenv:py{prev_ver}", "testenv:py", "tox"}


def test_show_config_pkg_env_skip(
    tox_project: ToxProjectCreator, patch_prev_py: Callable[[bool], Tuple[str, str]]
) -> None:
    prev_ver, impl = patch_prev_py(False)
    project = tox_project({"tox.ini": f"[tox]\nenv_list=py{prev_ver},py\n[testenv]\npackage=wheel"})
    result = project.run("c")
    result.assert_success()
    parser = ConfigParser()
    parser.read_string(result.out)
    sections = set(parser.sections())
    assert sections == {"testenv:.pkg", "tox", "testenv:py", f"testenv:py{prev_ver}"}


def test_show_config_select_only(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[tox]\nenv_list=\n a\n b"})
    result = project.run("c", "-e", "b,.pkg")
    result.assert_success()
    parser = ConfigParser()
    parser.read_string(result.out)
    sections = set(parser.sections())
    assert sections == {"testenv:.pkg", "testenv:b"}
