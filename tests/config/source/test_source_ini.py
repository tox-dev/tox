from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING

from tox.config.loader.section import Section
from tox.config.sets import ConfigSet, CoreConfigSet
from tox.config.source.ini import IniSource

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
        def register_config(self) -> None:
            self.add_config(
                keys=["a"],
                of_type=str,
                default="",
                desc="d",
            )

    config = tox_ini_conf("[testenv:foo]\n[custom:foo]\na = b")
    known_envs = list(config._src.envs(config.core))  # noqa: SLF001
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
