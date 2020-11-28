import os
import platform
import re
import sys

from packaging.version import Version

from tox.config.types import Command
from tox.pytest import MonkeyPatch, ToxProjectCreator
from tox.version import __version__


def test_show_config_default_run_env(tox_project: ToxProjectCreator, monkeypatch: MonkeyPatch) -> None:
    py_ver = sys.version_info[0:2]
    name = "py{}{}".format(*py_ver) if platform.python_implementation() == "CPython" else "pypy3"
    project = tox_project({"tox.ini": f"[tox]\nenv_list = {name}\n[testenv:{name}]\ncommands={{posargs}}"})
    result = project.run("c", "--", "magic")
    state = result.state
    assert state.args == ("c", "--", "magic")
    outcome = list(state.env_list(everything=True))
    assert outcome == [name]

    path = re.escape(str(project.path))
    sep = re.escape(str(os.sep))
    version = re.escape(Version(__version__).public)

    monkeypatch.delenv("TERM", raising=False)  # disable conditionally set flag
    if sys.platform == "win32":  # pragma: win32 cover
        p_env = ["COMSPEC", "MSYSTEM", "PATHEXT", "PROCESSOR_ARCHITECTURE", "SYSTEMROOT", "TEMP", "TMP", "USERPROFILE"]
    else:  # pragma: win32 no cover
        p_env = ["TMPDIR"]
    p_env.extend(["PIP_*", "VIRTUALENV_*", "http_proxy", "https_proxy", "no_proxy"])
    pass_env_str = "\n".join(f"      {re.escape(p)}" for p in sorted(p_env))[4:]

    expected = rf"""
    \[testenv:{name}\]
    type = VirtualEnvRunner
    base = testenv
    runner = virtualenv
    env_name = {name}
    env_dir = {path}{sep}\.tox4{sep}{name}
    env_tmp_dir = {path}{sep}\.tox4{sep}{name}{sep}tmp
    set_env =
      PIP_DISABLE_PIP_VERSION_CHECK=1
      VIRTUALENV_NO_PERIODIC_UPDATE=1
    pass_env =
    {pass_env_str}
    description =
    commands = magic
    commands_pre =
    commands_post =
    change_dir = {path}
    depends =
    parallel_show_output = False
    skip_install = False
    usedevelop = False
    package = sdist
    package_tox_env_type = virtualenv-pep-517-sdist
    package_env = \.package
    extras =
    base_python = {name}
    env_site_packages_dir = {path}{sep}\.tox4{sep}{name}{sep}.*
    env_python = {path}{sep}\.tox4{sep}{name}{sep}.*
    deps =\

    \[tox\]
    tox_root = {path}
    work_dir = {path}{sep}\.tox4
    temp_dir = {path}{sep}\.temp
    env_list = {name}
    min_version = {version}
    provision_tox_env = \.tox
    requires = tox>={version}
    no_package = False\
    skip_missing_interpreters = True
    """
    result.assert_out_err(expected, "", regex=True)


def test_commands(tox_project: ToxProjectCreator) -> None:
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
