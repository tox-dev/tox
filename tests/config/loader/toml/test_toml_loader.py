from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from tox.config.loader.api import ConfigLoadArgs, Override
from tox.config.loader.toml import TomlLoader
from tox.config.source.ini_section import IniSection

if TYPE_CHECKING:
    from configparser import ConfigParser


def test_toml_loader_keys(mk_toml_conf: Callable[[str], ConfigParser]) -> None:
    core = IniSection(None, "tox")
    loader = TomlLoader(core, mk_toml_conf("\n[tox]\n\na='b'\nc='d'\n\n"), [], core_section=core)
    assert loader.found_keys() == {"a", "c"}


def test_toml_loader_repr(mk_toml_conf: Callable[[str], ConfigParser]) -> None:
    core = IniSection(None, "tox")
    loader = TomlLoader(core, mk_toml_conf("\n[tox]\n\na='b'\nc='d'\n\n"), [Override("tox.a=1")], core_section=core)
    assert repr(loader) == "TomlLoader(section=tox, overrides={'a': [Override('tox.a=1')]})"


def test_toml_loader_has_section(mk_toml_conf: Callable[[str], ConfigParser]) -> None:
    core = IniSection(None, "tox")
    loader = TomlLoader(core, mk_toml_conf("[magic]\n[tox]\n\na='b'\nc='d'\n\n"), [], core_section=core)
    assert loader.get_section("magic") is not None


def test_toml_loader_has_no_section(mk_toml_conf: Callable[[str], ConfigParser]) -> None:
    core = IniSection(None, "tox")
    loader = TomlLoader(core, mk_toml_conf("[tox]\n\na='b'\nc='d'\n\n"), [], core_section=core)
    assert loader.get_section("magic") is None


def test_toml_loader_raw(mk_toml_conf: Callable[[str], ConfigParser]) -> None:
    core = IniSection(None, "tox")
    args = ConfigLoadArgs([], "name", None)
    loader = TomlLoader(core, mk_toml_conf("[tox]\na='b'"), [], core_section=core)
    result = loader.load(key="a", of_type=str, conf=None, factory=None, args=args)
    assert result == "b"
