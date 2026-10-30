from __future__ import annotations

import errno
import os
import sys
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

from tox.config.loader.api import Override
from tox.config.loader.memory import MemoryLoader
from tox.config.sets import ConfigSet
from tox.report import HandledError
from tox.tox_env.python.pip.req_file import PythonDeps

if TYPE_CHECKING:
    from collections.abc import Callable

    from pytest_mock import MockerFixture

    from tests.conftest import ToxIniCreator
    from tox.config.main import Config
    from tox.pytest import ToxProject, ToxProjectCreator, ToxRunOutcome


def test_empty_config_repr(empty_config: Config) -> None:
    text = repr(empty_config)
    assert str(empty_config.core["tox_root"]) in text
    assert "config_source=ToxIni" in text


def test_empty_conf_tox_envs(empty_config: Config) -> None:
    tox_env_keys = list(empty_config)
    assert tox_env_keys == []


def test_empty_conf_get(empty_config: Config) -> None:
    result = empty_config.get_env("magic")
    assert isinstance(result, ConfigSet)
    loaders = result["base"]
    assert loaders == ["testenv"]


def test_pos_args_path_error_masks_secret_flag(tox_project: ToxProjectCreator, mocker: MockerFixture) -> None:
    project: Final[ToxProject] = tox_project({
        "tox.toml": """\
[env_run_base]
package = "skip"
change_dir = "tests"
commands = [["python", "-c", "pass", { replace = "posargs", extend = true }]]
"""
    })
    (project.path / "tests").mkdir()
    original_exists: Final[Callable[[Path], bool]] = Path.exists

    def exists(path: Path) -> bool:
        if str(path) == "--token=hunter2":
            raise OSError(errno.ENAMETOOLONG, "File name too long")
        return original_exists(path)

    mocker.patch.object(Path, "exists", autospec=True, side_effect=exists)
    result: Final[ToxRunOutcome] = project.run("r", "-vv", "-e", "py", "--", "--token=hunter2")
    result.assert_success()
    assert "could not check if '--token=*******' is an existing path" in result.out
    assert "hunter2" not in result.out


def test_config_contains_env(tox_ini_conf: ToxIniCreator) -> None:
    config = tox_ini_conf("[tox]\nenv_list = py38\n[testenv]\n")
    assert "py38" in config
    assert "missing" not in config


def test_config_contains_empty_env_name(empty_config: Config) -> None:
    # a falsy (empty) environment name must still be reported as present, not swallowed by a truthiness check
    empty_config._extra_envs = [""]  # ruff:ignore[private-member-access]
    assert "" in empty_config


def test_config_some_envs(tox_ini_conf: ToxIniCreator) -> None:
    example = """
    [tox]
    env_list = py38, py37
    [testenv]
    deps = 1
        other: 2
    [testenv:magic]
    """
    config = tox_ini_conf(example)
    tox_env_keys = list(config)
    assert tox_env_keys == ["py38", "py37", "magic", "other"]

    config_set = config.get_env("py38")
    assert repr(config_set)
    assert isinstance(config_set, ConfigSet)
    assert list(config_set)


def test_config_overrides(tox_ini_conf: ToxIniCreator) -> None:
    conf = tox_ini_conf("[testenv]", override=[Override("testenv.c=ok")]).get_env("py")
    conf.add_config("c", of_type=str, default="d", desc="desc")
    assert conf["c"] == "ok"


def test_config_override_core_without_tox_section(tox_ini_conf: ToxIniCreator) -> None:
    conf = tox_ini_conf("[testenv]", override=[Override("tox.c=ok")]).core
    conf.add_config("c", of_type=str, default="d", desc="desc")
    assert conf["c"] == "ok"


def test_config_override_env_without_own_section(tox_ini_conf: ToxIniCreator) -> None:
    conf = tox_ini_conf("[testenv]", override=[Override("testenv:py.c=ok")]).get_env("py")
    conf.add_config("c", of_type=str, default="d", desc="desc")
    assert conf["c"] == "ok"


def test_config_override_wins_memory_loader(tox_ini_conf: ToxIniCreator) -> None:
    main_conf = tox_ini_conf("[testenv]", override=[Override("testenv.c=ok")])
    conf = main_conf.get_env("py", loaders=[MemoryLoader(c="something_else")])
    conf.add_config("c", of_type=str, default="d", desc="desc")
    assert conf["c"] == "ok"


def test_config_override_appends_to_list(tox_ini_conf: ToxIniCreator) -> None:
    example = """
    [testenv]
    passenv = foo
    """
    conf = tox_ini_conf(example, override=[Override("testenv.passenv+=bar")]).get_env("testenv")
    conf.add_config("passenv", of_type=list[str], default=[], desc="desc")
    assert conf["passenv"] == ["foo", "bar"]


def test_config_override_appends_to_dict(tox_ini_conf: ToxIniCreator) -> None:
    conf = tox_ini_conf("[testenv]\nfoo = a=1", override=[Override("testenv.foo+=b=2")]).get_env("testenv")
    conf.add_config("foo", of_type=dict[str, str], default={}, desc="desc")
    assert conf["foo"] == {"a": "1", "b": "2"}


def test_config_override_sequence(tox_ini_conf: ToxIniCreator) -> None:
    example = """
    [testenv]
    passenv = foo
    """
    overrides = [Override("testenv.passenv=bar"), Override("testenv.passenv+=baz")]
    conf = tox_ini_conf(example, override=overrides).get_env("testenv")
    conf.add_config("passenv", of_type=list[str], default=[], desc="desc")
    assert conf["passenv"] == ["bar", "baz"]


def test_config_override_appends_to_empty_list(tox_ini_conf: ToxIniCreator) -> None:
    conf = tox_ini_conf("[testenv]", override=[Override("testenv.passenv+=bar")]).get_env("testenv")
    conf.add_config("passenv", of_type=list[str], default=[], desc="desc")
    assert conf["passenv"] == ["bar"]


@pytest.mark.parametrize(
    ("ini_key", "override_key"),
    [
        pytest.param("passenv", "pass_env", id="ini_old_override_new"),
        pytest.param("pass_env", "passenv", id="ini_new_override_old"),
    ],
)
def test_config_override_append_alias_key(tox_ini_conf: ToxIniCreator, ini_key: str, override_key: str) -> None:
    example = f"""
    [testenv]
    {ini_key} = foo
    """
    conf = tox_ini_conf(example, override=[Override(f"testenv.{override_key}+=bar")]).get_env("testenv")
    conf.add_config(["pass_env", "passenv"], of_type=list[str], default=[], desc="desc")
    result = conf["pass_env"]
    assert "foo" in result
    assert "bar" in result


def test_config_override_appends_to_setenv(tox_ini_conf: ToxIniCreator) -> None:
    example = """
    [testenv]
    setenv =
      foo = bar
    """
    conf = tox_ini_conf(example, override=[Override("testenv.setenv+=baz=quux")]).get_env("testenv")
    assert conf["setenv"].load("foo") == "bar"
    assert conf["setenv"].load("baz") == "quux"


def test_config_override_appends_to_setenv_multiple(tox_ini_conf: ToxIniCreator) -> None:
    example = """
    [testenv]
    setenv =
      foo = bar
    """
    overrides = [Override("testenv.setenv+=baz=quux"), Override("testenv.setenv+=less=more")]
    conf = tox_ini_conf(example, override=overrides).get_env("testenv")
    assert conf["setenv"].load("foo") == "bar"
    assert conf["setenv"].load("baz") == "quux"
    assert conf["setenv"].load("less") == "more"


def test_config_override_sequential_processing(tox_ini_conf: ToxIniCreator) -> None:
    example = """
    [testenv]
    setenv =
      foo = bar
    """
    overrides = [Override("testenv.setenv+=a=b"), Override("testenv.setenv=c=d"), Override("testenv.setenv+=e=f")]
    conf = tox_ini_conf(example, override=overrides).get_env("testenv")
    with pytest.raises(KeyError):
        assert conf["setenv"].load("foo") == "bar"
    with pytest.raises(KeyError):
        assert conf["setenv"].load("a") == "b"
    assert conf["setenv"].load("c") == "d"
    assert conf["setenv"].load("e") == "f"


def test_config_override_appends_to_empty_setenv(tox_ini_conf: ToxIniCreator) -> None:
    conf = tox_ini_conf("[testenv]", override=[Override("testenv.setenv+=foo=bar")]).get_env("testenv")
    assert conf["setenv"].load("foo") == "bar"


def test_config_override_appends_to_pythondeps(tox_ini_conf: ToxIniCreator, tmp_path: Path) -> None:
    example = """
    [testenv]
    deps = foo
    """
    conf = tox_ini_conf(example, override=[Override("testenv.deps+=bar")]).get_env("testenv")
    conf.add_config(
        "deps",
        of_type=PythonDeps,
        factory=partial(PythonDeps.factory, tmp_path),
        default=PythonDeps("", root=tmp_path),
        desc="desc",
    )
    assert conf["deps"].lines() == ["foo", "bar"]


def test_config_multiple_overrides(tox_ini_conf: ToxIniCreator, tmp_path: Path) -> None:
    example = """
    [testenv]
    deps = foo
    """
    overrides = [Override("testenv.deps+=bar"), Override("testenv.deps+=baz")]
    conf = tox_ini_conf(example, override=overrides).get_env("testenv")
    conf.add_config(
        "deps",
        of_type=PythonDeps,
        factory=partial(PythonDeps.factory, tmp_path),
        default=PythonDeps("", root=tmp_path),
        desc="desc",
    )
    assert conf["deps"].lines() == ["foo", "bar", "baz"]


def test_config_override_appends_to_empty_pythondeps(tox_ini_conf: ToxIniCreator, tmp_path: Path) -> None:
    example = """
    [testenv]
    """
    conf = tox_ini_conf(example, override=[Override("testenv.deps+=bar")]).get_env("testenv")
    conf.add_config(
        "deps",
        of_type=PythonDeps,
        factory=partial(PythonDeps.factory, tmp_path),
        default=PythonDeps("", root=tmp_path),
        desc="desc",
    )
    assert conf["deps"].lines() == ["bar"]


def test_config_override_cannot_append(tox_ini_conf: ToxIniCreator) -> None:
    example = """
    [testenv]
    foo = 1
    """
    conf = tox_ini_conf(example, override=[Override("testenv.foo+=2")]).get_env("testenv")
    conf.add_config("foo", of_type=int, default=0, desc="desc")
    with pytest.raises(HandledError, match=r"failed to load testenv\.foo: Only able to append to lists and dicts"):
        conf["foo"]


def test_args_are_paths_when_disabled(tox_project: ToxProjectCreator) -> None:
    ini = "[testenv]\npackage=skip\ncommands={posargs}\nargs_are_paths=False"
    project = tox_project({"tox.ini": ini, "w": {"a.txt": "a"}})
    args = "magic.py", str(project.path), f"..{os.sep}tox.ini", "..", f"..{os.sep}.."
    result = project.run("c", "-e", "py", "-k", "commands", "--", *args, from_cwd=project.path / "w")
    result.assert_success()
    assert result.out == f"[testenv:py]\ncommands = magic.py {project.path} ..{os.sep}tox.ini .. ..{os.sep}..\n"


def test_args_are_paths_when_from_child_dir(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[testenv]\npackage=skip\ncommands={posargs}", "w": {"a.txt": "a"}})
    args = "magic.py", str(project.path), f"..{os.sep}tox.ini", "..", f"..{os.sep}.."
    result = project.run("c", "-e", "py", "-k", "commands", "--", *args, from_cwd=project.path / "w")
    result.assert_success()
    assert result.out == f"[testenv:py]\ncommands = magic.py {project.path} tox.ini . ..\n"


def test_args_are_paths_long_arg(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[testenv]\npackage=skip\ncommands={posargs}", "w": {"a.txt": "a"}})
    long_arg = "a" * 300  # exceeds filesystem filename length limit (typically 255)
    result = project.run("c", "-e", "py", "-k", "commands", "--", long_arg, from_cwd=project.path / "w")
    result.assert_success()
    assert result.out == f"[testenv:py]\ncommands = {long_arg}\n"


def test_args_are_paths_when_with_change_dir(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[testenv]\npackage=skip\ncommands={posargs}\nchange_dir=w", "w": {"a.txt": "a"}})
    args = "magic.py", str(project.path), "tox.ini", f"w{os.sep}a.txt", "w", "."
    result = project.run("c", "-e", "py", "-k", "commands", "--", *args)
    result.assert_success()
    assert result.out == f"[testenv:py]\ncommands = magic.py {project.path} ..{os.sep}tox.ini a.txt . ..\n"


_POSARGS: Final[str] = '{ replace = "posargs" }'
_POSARGS_EXTEND: Final[str] = '{ replace = "posargs", extend = true }'
_EXECUTABLE_NAME: Final[str] = "python.exe" if os.name == "nt" else "python"


@pytest.mark.parametrize(
    ("name", "config"),
    [
        pytest.param("tox.ini", "[testenv]\ncommands={posargs}", id="ini"),
        pytest.param("tox.ini", "[testenv]\ncommands=[]", id="ini-brackets"),
        pytest.param("tox.ini", "[testenv]\ncommands=- {posargs}", id="ini-ignore-exit-code"),
        pytest.param("tox.ini", "[testenv]\ncommands=-{posargs}", id="ini-ignore-exit-code-glued"),
        pytest.param("tox.ini", "[testenv]\ncommands=! {posargs}", id="ini-invert-exit-code"),
        pytest.param("tox.ini", "[testenv]\ncommands={env:NO_WRAPPER:} {posargs}", id="ini-after-empty"),
        pytest.param("tox.ini", "[testenv]\ncommands={env:NO_WRAPPER:{posargs}}", id="ini-default"),
        pytest.param("tox.ini", "[testenv]\ncommands={[a]b}\n[a]\nb={posargs}", id="ini-reference"),
        pytest.param("tox.toml", f"env_run_base.commands = [{_POSARGS}]", id="toml"),
        pytest.param("tox.toml", f"env_run_base.commands = [[{_POSARGS_EXTEND}]]", id="toml-extend"),
        pytest.param("tox.toml", f'env_run_base.commands = [["-", {_POSARGS_EXTEND}]]', id="toml-ignore-exit-code"),
        pytest.param("tox.toml", f'env_run_base.commands = [["!", {_POSARGS_EXTEND}]]', id="toml-invert-exit-code"),
        pytest.param(
            "tox.toml",
            f'env_run_base.commands = [{{ replace = "ref", of = ["a", "b"] }}]\na.b = {_POSARGS}',
            id="toml-reference",
        ),
        pytest.param(
            "tox.toml",
            f'env_run_base.commands = [{{ replace = "ref", of = ["a", "b"], extend = true }}]\na.b = [{_POSARGS}]',
            id="toml-reference-extend",
        ),
        pytest.param(
            "tox.toml",
            f'env_run_base.commands = [{{ replace = "if", condition = "env.NO", then = ["a"], else = {_POSARGS} }}]',
            id="toml-if",
        ),
    ],
)
def test_args_are_paths_keeps_program_name(tox_project: ToxProjectCreator, name: str, config: str) -> None:
    project: Final[ToxProject] = tox_project({name: config, "w": {"python": "", "a.txt": ""}})
    (project.path / "w" / "python").chmod(0o755)
    result: Final[ToxRunOutcome] = project.run(
        "c", "-e", "py", "-k", "commands", "--", "python", "python", "a.txt", from_cwd=project.path / "w"
    )
    result.assert_success()
    assert result.out == f"[testenv:py]\ncommands = python w{os.sep}python w{os.sep}a.txt\n"


def test_args_are_paths_keeps_install_program_name(tox_project: ToxProjectCreator) -> None:
    project: Final[ToxProject] = tox_project({
        "tox.toml": f"env_run_base.install_command = [{_POSARGS_EXTEND}]",
        "w": {"python": "", "a.txt": ""},
    })
    result: Final[ToxRunOutcome] = project.run(
        "c", "-e", "py", "-k", "install_command", "--", "python", "python", "a.txt", from_cwd=project.path / "w"
    )
    result.assert_success()
    assert result.out == f"[testenv:py]\ninstall_command = python w{os.sep}python w{os.sep}a.txt\n"


@pytest.mark.parametrize(
    ("name", "config", "program"),
    [
        pytest.param("tox.ini", "[testenv]\ncommands=env {posargs}", "env", id="ini-wrapper"),
        pytest.param(
            "tox.toml",
            f'env_run_base.commands = [["env", {_POSARGS_EXTEND}]]',
            "env",
            id="toml-wrapper",
        ),
        pytest.param("tox.ini", "[testenv]\ncommands=tool {posargs}", "tool", id="first-data-value"),
    ],
)
def test_args_are_paths_keeps_executable_first_value(
    tox_project: ToxProjectCreator, name: str, config: str, program: str
) -> None:
    project: Final[ToxProject] = tox_project({name: config, "w": {_EXECUTABLE_NAME: ""}})
    (project.path / "w" / _EXECUTABLE_NAME).chmod(0o755)
    result: Final[ToxRunOutcome] = project.run(
        "c", "-e", "py", "-k", "commands", "--", _EXECUTABLE_NAME, from_cwd=project.path / "w"
    )
    result.assert_success()
    assert result.out == f"[testenv:py]\ncommands = {program} {_EXECUTABLE_NAME}\n"


@pytest.mark.parametrize(
    ("name", "config", "expected"),
    [
        pytest.param("tox.ini", '[testenv]\ncommands="{posargs}"', "python", id="ini-quoted"),
        pytest.param("tox.ini", "[testenv]\ncommands=.{/}{posargs}", f".{os.sep}python", id="ini-suffix"),
        pytest.param("tox.toml", 'env_run_base.commands = [["{posargs}"]]', "python", id="toml"),
        pytest.param("tox.toml", 'env_run_base.commands = [["-", "{posargs}"]]', "python", id="toml-ignore-exit-code"),
        pytest.param("tox.toml", 'env_run_base.commands = [[".{/}{posargs}"]]', f".{os.sep}python", id="toml-suffix"),
        pytest.param(
            "tox.toml",
            'env_run_base.commands = [[{ replace = "env", name = "NO_WRAPPER", default = "{posargs}" }]]',
            "python",
            id="toml-env-default",
        ),
        pytest.param(
            "tox.toml",
            'env_run_base.commands = [[{ replace = "if", condition = "env.NO", then = "a", else = "{posargs}", '
            "extend = true }]]",
            "python",
            id="toml-if-extend",
        ),
    ],
)
def test_args_are_paths_keeps_program_name_within_word(
    tox_project: ToxProjectCreator, name: str, config: str, expected: str
) -> None:
    project: Final[ToxProject] = tox_project({name: config, "w": {"python": ""}})
    result: Final[ToxRunOutcome] = project.run(
        "c", "-e", "py", "-k", "commands", "--", "python", from_cwd=project.path / "w"
    )
    result.assert_success()
    assert result.out == f"[testenv:py]\ncommands = {expected}\n"


@pytest.mark.parametrize(
    ("name", "config"),
    [
        pytest.param("tox.ini", "[testenv]\ncommands={posargs}", id="ini"),
        pytest.param("tox.toml", f"env_run_base.commands = [{_POSARGS}]", id="toml"),
    ],
)
def test_args_are_paths_rewrites_program_path(tox_project: ToxProjectCreator, name: str, config: str) -> None:
    project: Final[ToxProject] = tox_project({name: config, "w": {_EXECUTABLE_NAME: ""}})
    (project.path / "w" / _EXECUTABLE_NAME).chmod(0o755)
    result: Final[ToxRunOutcome] = project.run(
        "c", "-e", "py", "-k", "commands", "--", f".{os.sep}{_EXECUTABLE_NAME}", from_cwd=project.path / "w"
    )
    result.assert_success()
    assert result.out == f"[testenv:py]\ncommands = w{os.sep}{_EXECUTABLE_NAME}\n"


@pytest.mark.parametrize(
    ("name", "config", "key", "prefix"),
    [
        pytest.param("tox.ini", "[testenv]\ncommands=a {posargs}", "commands", "a ", id="ini"),
        pytest.param("tox.ini", "[testenv]\ncommands=- a {posargs}", "commands", "a ", id="ini-ignore-exit-code"),
        pytest.param("tox.ini", "[testenv]\ncommands=a {[a]b}\n[a]\nb={posargs}", "commands", "a ", id="ini-reference"),
        pytest.param("tox.ini", "[testenv]\ndeps={posargs}", "deps", "", id="ini-deps"),
        pytest.param("tox.toml", f'env_run_base.commands = [["a", {_POSARGS_EXTEND}]]', "commands", "a ", id="toml"),
        pytest.param(
            "tox.toml",
            f'env_run_base.commands = [["-", "a", {_POSARGS_EXTEND}]]',
            "commands",
            "a ",
            id="toml-ignore-exit-code",
        ),
        pytest.param("tox.toml", 'env_run_base.commands = [["a", "{posargs}"]]', "commands", "a ", id="toml-str"),
        pytest.param(
            "tox.toml",
            f'env_run_base.commands = [["a", {{ replace = "ref", of = ["a", "b"], extend = true }}]]\na.b = {_POSARGS}',
            "commands",
            "a ",
            id="toml-reference",
        ),
        pytest.param("tox.toml", f"env_run_base.deps = [{_POSARGS_EXTEND}]", "deps", "", id="toml-deps"),
    ],
)
def test_args_are_paths_rewrites_name_after_program(
    tox_project: ToxProjectCreator, name: str, config: str, key: str, prefix: str
) -> None:
    project: Final[ToxProject] = tox_project({name: config, "w": {"python": ""}})
    result: Final[ToxRunOutcome] = project.run("c", "-e", "py", "-k", key, "--", "python", from_cwd=project.path / "w")
    result.assert_success()
    assert result.out == f"[testenv:py]\n{key} = {prefix}w{os.sep}python\n"


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks need privileges on Windows, and .. is unrolled lexically")
@pytest.mark.parametrize(
    "change_dir",
    [
        pytest.param("{env_tmp_dir}", id="environment-temp-directory"),
        pytest.param("{tox_root}{/}.tox{/}py{/}tmp", id="explicit-temp-directory"),
    ],
)
def test_args_are_paths_when_change_dir_behind_link(
    tox_project: ToxProjectCreator, tmp_path: Path, change_dir: str
) -> None:
    project: Final[ToxProject] = tox_project({
        "tox.ini": f"[testenv]\npackage=skip\ncommands=echo {{posargs}}\nchange_dir={change_dir}",
        "a.py": "",
    })
    (tmp_path / "work").mkdir()
    (project.path / ".tox").symlink_to(tmp_path / "work", target_is_directory=True)
    result: Final[ToxRunOutcome] = project.run("c", "-e", "py", "-k", "commands", "--", "a.py")
    result.assert_success()
    assert result.out == f"[testenv:py]\ncommands = echo ../../../{project.path.name}/a.py\n"


@pytest.mark.skipif(sys.platform == "win32", reason="creating symlinks requires privileges on Windows")
def test_args_are_paths_keeps_lexical_change_dir_on_windows(
    tox_project: ToxProjectCreator, tmp_path: Path, mocker: MockerFixture
) -> None:
    project: Final[ToxProject] = tox_project({
        "tox.ini": "[testenv]\npackage=skip\ncommands=echo {posargs}\nchange_dir={env_tmp_dir}",
        "a.py": "",
    })
    (tmp_path / "work").mkdir()
    (project.path / ".tox").symlink_to(tmp_path / "work", target_is_directory=True)
    mocker.patch("tox.config.main.sys", mocker.create_autospec(sys, platform="win32"))

    result: Final[ToxRunOutcome] = project.run("c", "-e", "py", "-k", "commands", "--", "a.py")

    result.assert_success()
    assert result.out == "[testenv:py]\ncommands = echo ../../../a.py\n"


@pytest.mark.timeout(60)
def test_get_env_reuses_config_across_package_flag(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.toml": """
env_list = ["a"]

[env.a]
package = "external"
package_env = ".build-a"

[env.".build-a"]
commands = [["python", "-c", "print('{env_tmp_dir}')"]]
package_glob = "{env_tmp_dir}/dist/*.whl"
""",
    })
    execute_calls = project.patch_execute(lambda r: 0)  # ruff:ignore[unused-lambda-argument]
    project.run("r", "-e", "a")
    calls = [(i[0][0].conf.name, i[0][3].cmd) for i in execute_calls.call_args_list]
    pkg_cmds = [cmd for name, cmd in calls if name == ".build-a"]
    assert pkg_cmds, f"no .build-a command found in {calls}"
    for cmd in pkg_cmds:
        cmd_str = " ".join(str(c) for c in cmd)
        assert "{env_tmp_dir}" not in cmd_str, f"env_tmp_dir not expanded in command: {cmd}"


def test_config_override_escaped_dot_namespace(tox_ini_conf: ToxIniCreator) -> None:
    example = """
    [testenv:3.14]
    deps = original
    """
    conf = tox_ini_conf(example, override=[Override("testenv:3\\.14.deps=replaced")]).get_env("3.14")
    conf.add_config("deps", of_type=str, default="", desc="desc")
    assert conf["deps"] == "replaced"


def test_relative_config_paths_resolve(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[tox]"})
    ini = str(Path(project.path.name) / "tox.ini")
    result = project.run("c", "-c", ini, "-k", "change_dir", "env_dir", from_cwd=project.path.parent)
    result.assert_success()
    expected = f"[testenv:py]\nchange_dir = {project.path}\nenv_dir = {project.path / '.tox' / 'py'}\n"
    assert result.out == expected


def test_empty_posarg_remains_empty(tox_project: ToxProjectCreator) -> None:
    project: Final[ToxProject] = tox_project({
        "tox.toml": """
[env.py]
package = "skip"
change_dir = "tests"
commands = [
  [
    "python",
    "-c",
    "import sys; print(sys.argv[1:])",
    { replace = "posargs", extend = true },
  ],
]
""",
    })
    (project.path / "tests").mkdir()
    result: Final[ToxRunOutcome] = project.run("r", "-e", "py", "--", "")
    result.assert_success()
    assert "['']" in result.out
