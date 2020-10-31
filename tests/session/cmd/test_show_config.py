import os
import platform
import re
import sys
import textwrap

from tox.pytest import MonkeyPatch, ToxProjectCreator
from tox.version import __version__


def test_list_empty(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": ""})
    outcome = project.run("c")
    outcome.assert_success()

    expected = textwrap.dedent(
        f"""
        [tox]
        tox_root = {project.path}
        work_dir = {project.path}{os.sep}.tox4
        temp_dir = {project.path}{os.sep}.temp
        env_list =
        skip_missing_interpreters = True
        min_version = {__version__}
        provision_tox_env = .tox
        requires = tox>={__version__}
        no_package = False
        """,
    ).lstrip()
    assert outcome.out == expected


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
    version = re.escape(__version__)

    monkeypatch.delenv("TERM", raising=False)  # disable conditionally set flag
    if sys.platform == "win32":  # pragma: win32 cover
        p_env = ["COMSPEC", "MSYSTEM", "PATHEXT", "PROCESSOR_ARCHITECTURE", "SYSTEMROOT", "TEMP", "TMP", "USERPROFILE"]
    else:  # pragma: win32 no cover
        p_env = ["TMPDIR"]
    p_env.extend(["PIP_*", "VIRTUALENV_*", "http_proxy", "https_proxy", "no_proxy"])
    pass_env_str = "\n".join(f"      {re.escape(p)}" for p in sorted(p_env))[4:]

    expected = rf"""
    \[tox\]
    tox_root = {path}
    work_dir = {path}{sep}\.tox4
    temp_dir = {path}{sep}\.temp
    env_list = {name}
    skip_missing_interpreters = True
    min_version = {version}
    provision_tox_env = \.tox
    requires = tox>={version}
    no_package = False

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
    deps =
    """
    result.assert_out_err(expected, "", regex=True)
