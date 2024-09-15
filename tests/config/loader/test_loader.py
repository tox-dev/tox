from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tox.config.cli.parse import get_options
from tox.config.loader.api import Loader, Override
from tox.config.loader.section import Section
from tox.config.loader.str_convert import StrConvert

if TYPE_CHECKING:
    from tox.config.main import Config
    from tox.pytest import CaptureFixture


@pytest.mark.parametrize("flag", ["-x", "--override"])
def test_override_incorrect(flag: str, capsys: CaptureFixture) -> None:
    with pytest.raises(SystemExit):
        get_options(flag, "magic")
    out, err = capsys.readouterr()
    assert not out
    assert "override magic has no = sign in it" in err


@pytest.mark.parametrize("flag", ["-x", "--override"])
def test_override_add(flag: str) -> None:
    parsed, _, __, ___, ____ = get_options(flag, "magic=true")
    assert len(parsed.override) == 1
    value = parsed.override[0]
    assert value.key == "magic"
    assert value.value == "true"
    assert not value.namespace
    assert value.append is False


@pytest.mark.parametrize("flag", ["-x", "--override"])
def test_override_append(flag: str) -> None:
    parsed, _, __, ___, ____ = get_options(flag, "magic+=true")
    assert len(parsed.override) == 1
    value = parsed.override[0]
    assert value.key == "magic"
    assert value.value == "true"
    assert not value.namespace
    assert value.append is True


@pytest.mark.parametrize("flag", ["-x", "--override"])
def test_override_multiple(flag: str) -> None:
    parsed, _, __, ___, ____ = get_options(flag, "magic+=1", flag, "magic+=2")
    assert len(parsed.override) == 2


def test_override_equals() -> None:
    assert Override("a=b") == Override("a=b")


def test_override_not_equals() -> None:
    assert Override("a=b") != Override("c=d")


def test_override_not_equals_different_type() -> None:
    assert Override("a=b") != 1


def test_override_repr() -> None:
    assert repr(Override("b.a=c")) == "Override('b.a=c')"


class SimpleLoader(StrConvert, Loader[str]):
    """Simple loader for tests."""

    def load_raw(self, key: str, conf: Config | None, env_name: str | None) -> str:  # type: ignore[empty-body]
        pass

    def found_keys(self) -> set[str]:  # type: ignore[empty-body]
        pass


def test_loader_repr() -> None:
    core = Section(None, "tox")
    loader = SimpleLoader(core, [Override("tox.a=1")])
    assert repr(loader) == "SimpleLoader(section=tox, overrides={'a': [Override('tox.a=1')]})"
