from __future__ import annotations

import os
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, List

import pytest

from tox.config.loader.api import Override
from tox.config.loader.memory import MemoryLoader
from tox.config.sets import ConfigSet
from tox.tox_env.python.pip.req_file import PythonDeps

if TYPE_CHECKING:
    from tests.conftest import ToxIniCreator
    from tox.config.main import Config
    from tox.pytest import ToxProjectCreator


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
    conf.add_config("passenv", of_type=List[str], default=[], desc="desc")
    assert conf["passenv"] == ["foo", "bar"]


def test_config_override_sequence(tox_ini_conf: ToxIniCreator) -> None:
    example = """
    [testenv]
    passenv = foo
    """
    overrides = [Override("testenv.passenv=bar"), Override("testenv.passenv+=baz")]
    conf = tox_ini_conf(example, override=overrides).get_env("testenv")
    conf.add_config("passenv", of_type=List[str], default=[], desc="desc")
    assert conf["passenv"] == ["bar", "baz"]


def test_config_override_appends_to_empty_list(tox_ini_conf: ToxIniCreator) -> None:
    conf = tox_ini_conf("[testenv]", override=[Override("testenv.passenv+=bar")]).get_env("testenv")
    conf.add_config("passenv", of_type=List[str], default=[], desc="desc")
    assert conf["passenv"] == ["bar"]


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
    with pytest.raises(ValueError, match="Only able to append to lists and dicts"):
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


def test_args_are_paths_when_with_change_dir(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[testenv]\npackage=skip\ncommands={posargs}\nchange_dir=w", "w": {"a.txt": "a"}})
    args = "magic.py", str(project.path), "tox.ini", f"w{os.sep}a.txt", "w", "."
    result = project.run("c", "-e", "py", "-k", "commands", "--", *args)
    result.assert_success()
    assert result.out == f"[testenv:py]\ncommands = magic.py {project.path} ..{os.sep}tox.ini a.txt . ..\n"


def test_relative_config_paths_resolve(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[tox]"})
    ini = str(Path(project.path.name) / "tox.ini")
    result = project.run("c", "-c", ini, "-k", "change_dir", "env_dir", from_cwd=project.path.parent)
    result.assert_success()
    expected = f"[testenv:py]\nchange_dir = {project.path}\nenv_dir = {project.path / '.tox' / 'py'}\n"
    assert result.out == expected
