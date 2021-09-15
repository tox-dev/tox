import os

from tests.conftest import ToxIniCreator
from tox.config.loader.api import Override
from tox.config.loader.memory import MemoryLoader
from tox.config.main import Config
from tox.config.sets import ConfigSet
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
    assert tox_env_keys == ["py38", "py37", "other", "magic"]

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
