from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING, Any

import pytest

from tox.session.cmd.show_config.json_format import colorize as colorize_json
from tox.session.cmd.show_config.toml_format import colorize as colorize_toml

if sys.version_info >= (3, 11):  # pragma: >=3.11 cover
    import tomllib
else:  # pragma: <3.11 cover
    import tomli as tomllib

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from tox.pytest import ToxProjectCreator

_FORMATS = [
    pytest.param("json", json.loads, id="json"),
    pytest.param("toml", tomllib.loads, id="toml"),
]


@pytest.mark.parametrize(("fmt", "loader"), _FORMATS)
def test_basic_structure(tox_project: ToxProjectCreator, fmt: str, loader: Callable[[str], Any]) -> None:
    project = tox_project({"tox.ini": "[tox]\nno_package = true\n[testenv]\ncommands = python -c pass"})
    result = project.run("c", "-e", "py", "--format", fmt)
    result.assert_success()
    env = loader(result.out)["env"]["py"]
    assert env["type"] == "VirtualEnvRunner"
    assert env["env_name"] == "py"


@pytest.mark.parametrize(("fmt", "loader"), _FORMATS)
def test_core_with_flag(tox_project: ToxProjectCreator, fmt: str, loader: Callable[[str], Any]) -> None:
    project = tox_project({"tox.ini": "[tox]\nno_package = true"})
    result = project.run("c", "-e", "py", "--core", "--format", fmt)
    result.assert_success()
    assert "tox_root" in loader(result.out)["tox"]


@pytest.mark.parametrize(("fmt", "loader"), _FORMATS)
def test_no_core_by_default(tox_project: ToxProjectCreator, fmt: str, loader: Callable[[str], Any]) -> None:
    project = tox_project({"tox.ini": "[tox]\nno_package = true"})
    result = project.run("c", "-e", "py", "--format", fmt)
    result.assert_success()
    assert "tox" not in loader(result.out)


@pytest.mark.parametrize(("fmt", "loader"), _FORMATS)
def test_core_with_all_envs(tox_project: ToxProjectCreator, fmt: str, loader: Callable[[str], Any]) -> None:
    project = tox_project({"tox.ini": "[tox]\nno_package = true\nenv_list = py"})
    result = project.run("c", "-e", "ALL", "--format", fmt)
    result.assert_success()
    assert "tox" in loader(result.out)


@pytest.mark.parametrize(("fmt", "loader"), _FORMATS)
def test_key_filtering(tox_project: ToxProjectCreator, fmt: str, loader: Callable[[str], Any]) -> None:
    project = tox_project({"tox.ini": "[tox]\nno_package = true\n[testenv]\ncommands = python -c pass"})
    result = project.run("c", "-e", "py", "--format", fmt, "-k", "env_name", "commands")
    result.assert_success()
    env = loader(result.out)["env"]["py"]
    assert "env_name" in env
    assert "commands" in env
    assert "type" not in env


@pytest.mark.parametrize(("fmt", "loader"), _FORMATS)
def test_native_types(tox_project: ToxProjectCreator, fmt: str, loader: Callable[[str], Any]) -> None:
    project = tox_project({"tox.ini": "[tox]\nno_package = true\n[testenv]\npackage = skip"})
    result = project.run("c", "-e", "py", "--format", fmt, "-k", "suicide_timeout", "allowlist_externals")
    result.assert_success()
    env = loader(result.out)["env"]["py"]
    assert isinstance(env["suicide_timeout"], float)
    assert isinstance(env["allowlist_externals"], list)


@pytest.mark.parametrize(("fmt", "loader"), _FORMATS)
def test_multiple_envs(tox_project: ToxProjectCreator, fmt: str, loader: Callable[[str], Any]) -> None:
    project = tox_project({"tox.ini": "[tox]\nno_package = true\nenv_list = a,b\n[testenv]\npackage = skip"})
    result = project.run("c", "-e", "a,b", "--format", fmt)
    result.assert_success()
    data = loader(result.out)
    assert "a" in data["env"]
    assert "b" in data["env"]


@pytest.mark.parametrize(("fmt", "loader"), _FORMATS)
def test_unused_keys(tox_project: ToxProjectCreator, fmt: str, loader: Callable[[str], Any]) -> None:
    project = tox_project({"tox.ini": "[testenv:py]\nmagical = yes\nmagic = yes"})
    result = project.run("c", "-e", "py", "--format", fmt)
    result.assert_success()
    assert sorted(loader(result.out)["env"]["py"]["unused"]) == ["magic", "magical"]


@pytest.mark.parametrize(("fmt", "loader"), _FORMATS)
def test_no_unused_with_key_filter(tox_project: ToxProjectCreator, fmt: str, loader: Callable[[str], Any]) -> None:
    project = tox_project({"tox.ini": "[testenv:py]\nmagical = yes"})
    result = project.run("c", "-e", "py", "--format", fmt, "-k", "env_name")
    result.assert_success()
    assert "unused" not in loader(result.out)["env"]["py"]


@pytest.mark.parametrize(("fmt", "loader"), _FORMATS)
def test_output_to_file(tox_project: ToxProjectCreator, fmt: str, loader: Callable[[str], Any], tmp_path: Path) -> None:
    out_file = tmp_path / f"config.{fmt}"
    project = tox_project({"tox.ini": "[tox]\nno_package = true"})
    result = project.run("c", "-e", "py", "--format", fmt, "-o", str(out_file))
    result.assert_success()
    assert not result.out
    assert "py" in loader(out_file.read_text())["env"]


@pytest.mark.parametrize("fmt", [pytest.param("json", id="json"), pytest.param("toml", id="toml")])
def test_file_output_no_ansi(tox_project: ToxProjectCreator, fmt: str, tmp_path: Path) -> None:
    out_file = tmp_path / f"config.{fmt}"
    project = tox_project({"tox.ini": "[tox]\nno_package = true"})
    result = project.run("c", "-e", "py", "--format", fmt, "-o", str(out_file))
    result.assert_success()
    assert "\x1b[" not in out_file.read_text()


@pytest.mark.parametrize(("fmt", "loader"), _FORMATS)
def test_set_env(tox_project: ToxProjectCreator, fmt: str, loader: Callable[[str], Any]) -> None:
    project = tox_project({"tox.ini": "[tox]\nno_package = true\n[testenv]\nset_env =\n    A=1\n    B=hello"})
    result = project.run("c", "-e", "py", "--format", fmt, "-k", "set_env")
    result.assert_success()
    se = loader(result.out)["env"]["py"]["set_env"]
    assert se["A"] == "1"
    assert se["B"] == "hello"


@pytest.mark.parametrize(("fmt", "loader"), _FORMATS)
def test_deps(tox_project: ToxProjectCreator, fmt: str, loader: Callable[[str], Any]) -> None:
    project = tox_project({"tox.ini": "[tox]\nno_package = true\n[testenv]\ndeps =\n    pytest\n    flask>=2.0"})
    result = project.run("c", "-e", "py", "--format", fmt, "-k", "deps")
    result.assert_success()
    deps = loader(result.out)["env"]["py"]["deps"]
    assert isinstance(deps, list)
    assert "pytest" in deps
    assert "flask>=2.0" in deps


def test_json_exception(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[testenv:a]\nbase_python = missing-python"})
    result = project.run("c", "-e", "a", "--format", "json", "-k", "env_site_packages_dir", raise_on_config_fail=False)
    result.assert_failed(code=-1)
    assert "error" in json.loads(result.out)["env"]["a"]["env_site_packages_dir"]


def test_json_pass_env(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[tox]\nno_package = true\n[testenv]\npass_env = HOME,PATH"})
    result = project.run("c", "-e", "py", "--format", "json", "-k", "pass_env")
    result.assert_success()
    pe = json.loads(result.out)["env"]["py"]["pass_env"]
    assert isinstance(pe, list)
    assert "HOME" in pe


def test_json_alias_key(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[tox]\nno_package = true"})
    result = project.run("c", "-e", "py", "--format", "json", "-k", "setenv")
    result.assert_success()
    assert "set_env" in json.loads(result.out)["env"]["py"]


def test_json_valid_output(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[tox]\nno_package = true"})
    result = project.run("c", "-e", "py", "--format", "json")
    result.assert_success()
    json.loads(result.out)


def test_json_native_types_approx(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[tox]\nno_package = true\n[testenv]\npackage = skip"})
    result = project.run("c", "-e", "py", "--format", "json", "-k", "suicide_timeout")
    result.assert_success()


@pytest.mark.parametrize("fmt", [pytest.param("json", id="json"), pytest.param("toml", id="toml")])
def test_key_filter_skips_missing(tox_project: ToxProjectCreator, fmt: str) -> None:
    project = tox_project({"tox.ini": "[tox]\nno_package = true"})
    result = project.run("c", "-e", "py", "--format", fmt, "-k", "no_such_key")
    result.assert_success()


def test_core_exception_json(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[testenv:a]\nbase_python = missing-python"})
    result = project.run(
        "c", "-e", "a", "--core", "--format", "json", "-k", "env_site_packages_dir", raise_on_config_fail=False
    )
    result.assert_failed(code=-1)
    data = json.loads(result.out)
    assert "error" in data["env"]["a"]["env_site_packages_dir"]
    assert "tox" in data


def testcolorize_json() -> None:
    result = colorize_json('{\n  "key": "val"\n}')
    assert "\x1b[" in result
    assert "key" in result


def testcolorize_toml() -> None:
    result = colorize_toml("[env.py]\nname = true")
    assert "\x1b[" in result
    assert "env.py" in result
