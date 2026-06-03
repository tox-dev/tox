from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tox.config.cli.parse import get_options
from tox.config.loader.api import Override, apply_overrides_to_raw

if TYPE_CHECKING:
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


@pytest.mark.parametrize(
    ("raw", "namespace", "key", "value", "append", "expected_str"),
    [
        pytest.param("env.3\\.14.deps=foo", "env.3.14", "deps", "foo", False, "env.3\\.14.deps=foo", id="escaped_dot"),
        pytest.param("a\\.b\\.c.key=val", "a.b.c", "key", "val", False, "a\\.b\\.c.key=val", id="multiple_escaped"),
        pytest.param(
            "env.3\\.14.deps+=bar", "env.3.14", "deps", "bar", True, "env.3\\.14.deps+=bar", id="escaped_append"
        ),
        pytest.param("testenv.deps=foo", "testenv", "deps", "foo", False, "testenv.deps=foo", id="no_escape_compat"),
        pytest.param(
            "test\\env.key=val", "test\\env", "key", "val", False, "test\\env.key=val", id="backslash_not_before_dot"
        ),
    ],
)
def test_override_escaped_dot(raw: str, namespace: str, key: str, value: str, append: bool, expected_str: str) -> None:
    override = Override(raw)
    assert override.namespace == namespace
    assert override.key == key
    assert override.value == value
    assert override.append is append
    assert str(override) == expected_str


@pytest.mark.parametrize(
    ("override", "raw", "expected"),
    [
        pytest.param("ns.k=blue", ["red"], ["blue"], id="list-replace"),
        pytest.param("ns.k+=blue", ["red"], ["red", "blue"], id="list-append"),
        pytest.param("ns.k=blue", "red", "blue", id="scalar-replace"),
        pytest.param("ns.k+=blue", "red", "red\nblue", id="str-append"),
        pytest.param("ns.k=a=1", {"b": "2"}, {"a": "1"}, id="dict-replace"),
        pytest.param("ns.k+=a=1", {"b": "2"}, {"b": "2", "a": "1"}, id="dict-append"),
    ],
)
def test_apply_overrides_to_raw(override: str, raw: object, expected: object) -> None:
    assert apply_overrides_to_raw([Override(override)], "k", raw) == expected


def test_apply_overrides_to_raw_ignores_other_keys() -> None:
    assert apply_overrides_to_raw([Override("ns.other=blue")], "k", ["red"]) == ["red"]


def test_apply_overrides_to_raw_append_unsupported_type() -> None:
    with pytest.raises(ValueError, match="Only able to append to lists, dicts and strings"):
        apply_overrides_to_raw([Override("ns.k+=1")], "k", 0)
