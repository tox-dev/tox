from __future__ import annotations

import pytest

from tox.config.source.toml_section import TomlSection


def test_toml_section_immutable_prefix() -> None:
    assert TomlSection(["a"], "b").prefix == ("a",)


@pytest.mark.parametrize(
    ("section", "key"),
    [
        (TomlSection((), "a"), "a"),
        (TomlSection(("a"), "b"), "a:b"),
        (TomlSection(("a", "b"), "c"), "a:b:c"),
    ],
)
def test_toml_section_key(section: TomlSection, key: str) -> None:
    assert section.key == key


@pytest.mark.parametrize(
    ("key", "section"),
    [
        ("a", TomlSection((), "a")),
        ("a:b", TomlSection(("a"), "b")),
        ("a:b:c", TomlSection(("a", "b"), "c")),
    ],
)
def test_toml_section_from_key(key: str, section: TomlSection) -> None:
    assert section.from_key(key) == section


def test_toml_section_test_env() -> None:
    assert TomlSection.test_env("example") == TomlSection(("tox", "env"), "example")


@pytest.mark.parametrize(
    ("section", "is_test_env"),
    [
        (TomlSection((), "a"), False),
        (TomlSection(("tox"), "a"), False),
        (TomlSection(("env",), "a"), False),
        (TomlSection(("tox", "env"), "a"), True),
        # The default testenv is not a testenv itself.
        (TomlSection(("tox", "env"), "testenv"), False),
        (TomlSection(("tox", "other"), "a"), False),
        (TomlSection(("tox", "env", "other"), "a"), False),
    ],
)
def test_toml_section_is_test_env(section: TomlSection, is_test_env: bool) -> None:
    assert section.is_test_env == is_test_env
