from configparser import ConfigParser
from typing import Callable

import pytest

from tox.config.loader.api import Override
from tox.config.loader.ini import IniLoader


def test_ini_loader_keys(mk_ini_conf: Callable[[str], ConfigParser]) -> None:
    loader = IniLoader("tox", mk_ini_conf("\n[tox]\n\na=b\nc=d\n\n"), [])
    assert loader.found_keys() == {"a", "c"}


def test_ini_loader_repr(mk_ini_conf: Callable[[str], ConfigParser]) -> None:
    loader = IniLoader("tox", mk_ini_conf("\n[tox]\n\na=b\nc=d\n\n"), [Override("tox.a=1")])
    assert repr(loader) == "IniLoader(section=<Section: tox>, overrides={'a': Override('tox.a=1')})"


def test_ini_loader_has_section(mk_ini_conf: Callable[[str], ConfigParser]) -> None:
    loader = IniLoader("tox", mk_ini_conf("[magic]\n[tox]\n\na=b\nc=d\n\n"), [])
    assert loader.get_section("magic") is not None


def test_ini_loader_has_no_section(mk_ini_conf: Callable[[str], ConfigParser]) -> None:
    loader = IniLoader("tox", mk_ini_conf("[tox]\n\na=b\nc=d\n\n"), [])
    assert loader.get_section("magic") is None


def test_ini_loader_raw(mk_ini_conf: Callable[[str], ConfigParser]) -> None:
    loader = IniLoader("tox", mk_ini_conf("[tox]\na=b"), [])
    result = loader.load(key="a", of_type=str, conf=None, env_name=None, chain=[])
    assert result == "b"


@pytest.mark.parametrize("sep", ["\n", "\r\n"])
def test_ini_loader_raw_strip_escaped_newline(mk_ini_conf: Callable[[str], ConfigParser], sep: str) -> None:
    loader = IniLoader("tox", mk_ini_conf(f"[tox]{sep}a=b\\{sep} c"), [])
    result = loader.load(key="a", of_type=str, conf=None, env_name=None, chain=[])
    assert result == "bc"
