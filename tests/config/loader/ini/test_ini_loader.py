from __future__ import annotations

from typing import TYPE_CHECKING, Callable

import pytest

from tox.config.loader.api import ConfigLoadArgs, Override
from tox.config.loader.ini import IniLoader
from tox.config.source.ini_section import IniSection

if TYPE_CHECKING:
    from configparser import ConfigParser


def test_ini_loader_keys(mk_ini_conf: Callable[[str], ConfigParser]) -> None:
    core = IniSection(None, "tox")
    loader = IniLoader(core, mk_ini_conf("\n[tox]\n\na=b\nc=d\n\n"), [], core_section=core)
    assert loader.found_keys() == {"a", "c"}


def test_ini_loader_repr(mk_ini_conf: Callable[[str], ConfigParser]) -> None:
    core = IniSection(None, "tox")
    loader = IniLoader(core, mk_ini_conf("\n[tox]\n\na=b\nc=d\n\n"), [Override("tox.a=1")], core_section=core)
    assert repr(loader) == "IniLoader(section=tox, overrides={'a': [Override('tox.a=1')]})"


def test_ini_loader_has_section(mk_ini_conf: Callable[[str], ConfigParser]) -> None:
    core = IniSection(None, "tox")
    loader = IniLoader(core, mk_ini_conf("[magic]\n[tox]\n\na=b\nc=d\n\n"), [], core_section=core)
    assert loader.get_section("magic") is not None


def test_ini_loader_has_no_section(mk_ini_conf: Callable[[str], ConfigParser]) -> None:
    core = IniSection(None, "tox")
    loader = IniLoader(core, mk_ini_conf("[tox]\n\na=b\nc=d\n\n"), [], core_section=core)
    assert loader.get_section("magic") is None


def test_ini_loader_raw(mk_ini_conf: Callable[[str], ConfigParser]) -> None:
    core = IniSection(None, "tox")
    args = ConfigLoadArgs([], "name", None)
    loader = IniLoader(core, mk_ini_conf("[tox]\na=b"), [], core_section=core)
    result = loader.load(key="a", of_type=str, conf=None, factory=None, args=args)
    assert result == "b"


@pytest.mark.parametrize("sep", ["\n", "\r\n"])
def test_ini_loader_raw_strip_escaped_newline(mk_ini_conf: Callable[[str], ConfigParser], sep: str) -> None:
    core = IniSection(None, "tox")
    args = ConfigLoadArgs([], "name", None)
    loader = IniLoader(core, mk_ini_conf(f"[tox]{sep}a=b\\{sep} c"), [], core_section=core)
    result = loader.load(key="a", of_type=str, conf=None, factory=None, args=args)
    assert result == "bc"


@pytest.mark.parametrize(
    ("case", "result"),
    [
        ("# a", ""),
        ("#", ""),
        ("a # w", "a"),
        ("a\t# w", "a"),
        ("a# w", "a"),
        ("a\\# w", "a# w"),
        ("#a\n b # w\n w", "b\nw"),
    ],
)
def test_ini_loader_strip_comments(mk_ini_conf: Callable[[str], ConfigParser], case: str, result: str) -> None:
    core = IniSection(None, "tox")
    args = ConfigLoadArgs([], "name", None)
    loader = IniLoader(core, mk_ini_conf(f"[tox]\na={case}"), [], core_section=core)
    outcome = loader.load(key="a", of_type=str, conf=None, factory=None, args=args)
    assert outcome == result
