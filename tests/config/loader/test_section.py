from __future__ import annotations

from typing import Any

import pytest

from tox.config.loader.section import Section


@pytest.mark.parametrize(
    ("section", "outcome"),
    [
        (Section("a", "b"), "a:b"),
        (Section(None, "a"), "a"),
    ],
)
def test_section_str(section: Section, outcome: str) -> None:
    assert str(section) == outcome


@pytest.mark.parametrize(
    ("section", "outcome"),
    [
        (Section("a", "b"), "Section(prefix='a', name='b')"),
        (Section(None, "a"), "Section(prefix=None, name='a')"),
    ],
)
def test_section_repr(section: Section, outcome: str) -> None:
    assert repr(section) == outcome


def test_section_eq() -> None:
    assert Section(None, "a") == Section(None, "a")


@pytest.mark.parametrize(
    ("section", "other"),
    [
        (Section("a", "b"), "a-b"),
        (Section(None, "a"), Section("b", "a")),
        (Section("a", "b"), Section("a", "c")),
    ],
)
def test_section_not_eq(section: Section, other: Any) -> None:
    assert section != other
