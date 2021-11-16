from __future__ import annotations

import pytest

from tox.config.cli.parse import get_options
from tox.config.loader.api import Override
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
    assert value.namespace == ""


def test_override_equals() -> None:
    assert Override("a=b") == Override("a=b")


def test_override_not_equals() -> None:
    assert Override("a=b") != Override("c=d")


def test_override_not_equals_different_type() -> None:
    assert Override("a=b") != 1


def test_override_repr() -> None:
    assert repr(Override("b.a=c")) == "Override('b.a=c')"
