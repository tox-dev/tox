from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING

import pytest

from tox.config.loader.section import Section
from tox.config.sets import ConfigSet, CoreConfigSet
from tox.config.source.ini import IniSource
from tox.util.typing_compat import override

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

    from tests.conftest import ToxIniCreator


def test_source_ini_with_interpolated(tmp_path: Path) -> None:
    loader = IniSource(tmp_path, content="[tox]\na = %(c)s").get_loader(Section(None, "tox"), {})
    assert loader is not None
    loader.load_raw("a", None, None)


def test_source_ini_ignore_non_testenv_sections(tmp_path: Path, mocker: MockerFixture) -> None:
    core = mocker.create_autospec(CoreConfigSet, instance=True)
    core.__getitem__ = lambda _self, key: [] if key == "env_list" else None
    loader = IniSource(tmp_path, content="[mypy-rest_framework.compat.*]")
    res = list(loader.envs(core))
    assert not res


def test_source_ini_ignore_invalid_factor_filters(tmp_path: Path, mocker: MockerFixture) -> None:
    core = mocker.create_autospec(CoreConfigSet, instance=True)
    core.__getitem__ = lambda _self, key: [] if key == "env_list" else None
    loader = IniSource(tmp_path, content="[a]\nb= if c: d")
    res = list(loader.envs(core))
    assert not res


def test_source_ini_custom_non_testenv_sections(tox_ini_conf: ToxIniCreator) -> None:
    """Validate that a plugin can load section with custom prefix overlapping testenv name."""

    class CustomConfigSet(ConfigSet):
        @override
        def register_config(self) -> None:
            self.add_config(
                keys=["a"],
                of_type=str,
                default="",
                desc="d",
            )

    config = tox_ini_conf("[testenv:foo]\n[custom:foo]\na = b")
    known_envs = list(config._src.envs(config.core))  # ruff:ignore[private-member-access]
    assert known_envs
    custom_section = config.get_section_config(
        section=Section("custom", "foo"),
        base=[],
        of_type=CustomConfigSet,
        for_env=None,
    )
    assert custom_section["a"] == "b"


def test_source_ini_unicode_characters(tmp_path: Path) -> None:
    """Test that INI files with unicode characters are read correctly."""
    ini_file = tmp_path / "tox.ini"
    content = """
        [tox]
        description = Test with emoji ❌ and unicode ✨
        """
    ini_file.write_text(dedent(content), encoding="utf-8")
    loader = IniSource(ini_file).get_loader(Section(None, "tox"), {})
    assert loader is not None
    desc = loader.load_raw("description", None, None)
    assert desc == "Test with emoji ❌ and unicode ✨"


def test_source_ini_utf8_bom(tmp_path: Path) -> None:
    ini_file = tmp_path / "tox.ini"
    content = """
        [tox]
        description = Test with a BOM
        """
    ini_file.write_bytes(b"\xef\xbb\xbf" + dedent(content).encode("utf-8"))
    loader = IniSource(ini_file).get_loader(Section(None, "tox"), {})
    assert loader is not None
    desc = loader.load_raw("description", None, None)
    assert desc == "Test with a BOM"


def test_source_ini_non_utf8_file_still_raises(tmp_path: Path) -> None:
    ini_file = tmp_path / "tox.ini"
    ini_file.write_bytes(b"[tox]\ndescription = \xff\xfe\n")
    with pytest.raises(UnicodeDecodeError):
        IniSource(ini_file)


def test_source_ini_bom_in_the_middle_is_kept(tmp_path: Path) -> None:
    ini_file = tmp_path / "tox.ini"
    ini_file.write_text("[tox]\ndescription = a\ufeffb\n", encoding="utf-8")
    loader = IniSource(ini_file).get_loader(Section(None, "tox"), {})
    assert loader is not None
    assert loader.load_raw("description", None, None) == "a\ufeffb"


def test_source_ini_bom_only_behaves_like_empty_config(tmp_path: Path) -> None:
    bom_only = tmp_path / "bom.ini"
    bom_only.write_bytes(b"\xef\xbb\xbf")
    assert list(IniSource(bom_only).sections()) == []


def test_source_ini_content_leading_utf8_bom_is_stripped(tmp_path: Path) -> None:
    loader = IniSource(tmp_path, content="\ufeff[tox]\ndescription = bom").get_loader(Section(None, "tox"), {})
    assert loader is not None
    assert loader.load_raw("description", None, None) == "bom"


@pytest.mark.parametrize(
    ("content", "match"),
    [
        pytest.param("\ufeff\ufeff[tox]\ndescription = two", "File contains no section headers", id="two-leading-boms"),
        pytest.param(
            "[tox]\ndescription = a\n\ufeff[testenv]\nx = 1",
            "Source contains parsing errors",
            id="bom-before-later-section",
        ),
        pytest.param(" \ufeff[tox]\ndescription = spaced", "File contains no section headers", id="space-then-bom"),
    ],
)
def test_source_ini_content_other_bom_positions_keep_failing(tmp_path: Path, content: str, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        IniSource(tmp_path, content=content)


def test_source_ini_content_bom_inside_a_value_is_kept(tmp_path: Path) -> None:
    loader = IniSource(tmp_path, content="[tox]\ndescription = a\ufeffb").get_loader(Section(None, "tox"), {})
    assert loader is not None
    assert loader.load_raw("description", None, None) == "a\ufeffb"
