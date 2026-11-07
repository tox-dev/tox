from __future__ import annotations

import pytest

from tox.config.loader.section import Section


@pytest.mark.parametrize(
    ("section", "outcome"),
    [
        pytest.param(
            Section("a", "b"), "a:b", id="section-lparen-quote-a-quote-comma-space-quote-b-quote-rparen-a-colon-b"
        ),
        pytest.param(Section(None, "a"), "a", id="section-lparen-none-comma-space-quote-a-quote-rparen-a"),
    ],
)
def test_section_str(section: Section, outcome: str) -> None:
    assert str(section) == outcome


@pytest.mark.parametrize(
    ("section", "outcome"),
    [
        pytest.param(
            Section("a", "b"),
            "Section(prefix='a', name='b')",
            id="section-lparen-quote-a-quote-comma-space-quote-b-quote-rparen-section-lparen-prefix-equal-quote-a-quote-comma-space-name-equal-quote-b-quote-rparen",
        ),
        pytest.param(
            Section(None, "a"),
            "Section(prefix=None, name='a')",
            id="section-lparen-none-comma-space-quote-a-quote-rparen-section-lparen-prefix-equal-none-comma-space-name-equal-quote-a-quote-rparen",
        ),
    ],
)
def test_section_repr(section: Section, outcome: str) -> None:
    assert repr(section) == outcome


def test_section_eq() -> None:
    assert Section(None, "a") == Section(None, "a")


@pytest.mark.parametrize(
    ("section", "other"),
    [
        pytest.param(
            Section("a", "b"), "a-b", id="section-lparen-quote-a-quote-comma-space-quote-b-quote-rparen-a-dash-b"
        ),
        pytest.param(
            Section(None, "a"),
            Section("b", "a"),
            id="section-lparen-none-comma-space-quote-a-quote-rparen-section-lparen-quote-b-quote-comma-space-quote-a-quote-rparen",
        ),
        pytest.param(
            Section("a", "b"),
            Section("a", "c"),
            id="section-lparen-quote-a-quote-comma-space-quote-b-quote-rparen-section-lparen-quote-a-quote-comma-space-quote-c-quote-rparen",
        ),
    ],
)
def test_section_not_eq(section: Section, other: Section) -> None:
    assert section != other
