"""Support for TOML config sources.

This is experimental API! Expect things to be broken.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import chain
from typing import TYPE_CHECKING, Iterable, Iterator

import tomllib

from tox.config.loader.ini.factor import find_envs
from tox.config.loader.section import Section
from tox.config.loader.toml import TomlLoader

from .api import Source
from .ini_section import CORE, PKG_ENV_PREFIX, TEST_ENV_PREFIX, IniSection

if TYPE_CHECKING:
    from pathlib import Path

    from tox.config.loader.api import OverrideMap
    from tox.config.sets import ConfigSet


class TomlSource(Source):
    """Configuration sourced from a toml file (such as tox.toml).

    This is experimental API! Expect things to be broken.
    """

    CORE_SECTION = CORE

    def __init__(self, path: Path, content: str | None = None) -> None:
        super().__init__(path)
        if content is None:
            if not path.exists():
                raise ValueError
            content = path.read_text()
        self._raw = tomllib.loads(content)
        self._section_mapping: defaultdict[str, list[str]] = defaultdict(list)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(path={self.path})"

    def transform_section(self, section: Section) -> Section:  # noqa: PLR6301
        return IniSection(section.prefix, section.name)

    def get_loader(self, section: Section, override_map: OverrideMap) -> TomlLoader | None:
        # look up requested section name in the generative testenv mapping to find the real config source
        for key in self._section_mapping.get(section.name) or []:
            if section.prefix is None or Section.from_key(key).prefix == section.prefix:
                break
        else:
            # if no matching section/prefix is found, use the requested section key as-is (for custom prefixes)
            key = section.key
        if key in self._raw:
            return TomlLoader(
                section=section,
                raw=self._raw,
                overrides=override_map.get(section.key, []),
                core_section=self.CORE_SECTION,
                section_key=key,
            )
        return None

    def get_base_sections(self, base: list[str], in_section: Section) -> Iterator[Section]:  # noqa: PLR6301
        for a_base in base:
            section = IniSection.from_key(a_base)
            yield section  # the base specifier is explicit
            if in_section.prefix is not None:  # no prefix specified, so this could imply our own prefix
                yield IniSection(in_section.prefix, a_base)

    def sections(self) -> Iterator[IniSection]:
        for key in self._raw:
            yield IniSection.from_key(key)

    def envs(self, core_config: ConfigSet) -> Iterator[str]:
        seen = set()
        for name in self._discover_tox_envs(core_config):
            if name not in seen:
                seen.add(name)
                yield name

    def _discover_tox_envs(self, core_config: ConfigSet) -> Iterator[str]:
        def register_factors(envs: Iterable[str]) -> None:
            known_factors.update(chain.from_iterable(e.split("-") for e in envs))

        explicit = list(core_config["env_list"])
        yield from explicit
        known_factors: set[str] = set()
        register_factors(explicit)

        # discover all additional defined environments, including generative section headers
        for section in self.sections():
            if section.is_test_env:
                register_factors(section.names)
                for name in section.names:
                    self._section_mapping[name].append(section.key)
                    yield name
        # add all conditional markers that are not part of the explicitly defined sections
        for section in self.sections():
            yield from self._discover_from_section(section, known_factors)

    def _discover_from_section(self, section: IniSection, known_factors: set[str]) -> Iterator[str]:
        for value in self._raw[section.key].values():
            if isinstance(value, bool):
                # It's not a value with env definition.
                continue
            # XXX: We munch the value to multiline string to parse it by the library utils.
            merged_value = "\n".join(str(v) for v in tuple(value))
            for env in find_envs(merged_value):
                if set(env.split("-")) - known_factors:
                    yield env

    def get_tox_env_section(self, item: str) -> tuple[Section, list[str], list[str]]:  # noqa: PLR6301
        return IniSection.test_env(item), [TEST_ENV_PREFIX], [PKG_ENV_PREFIX]

    def get_core_section(self) -> Section:
        return self.CORE_SECTION


class ToxToml(TomlSource):
    """Configuration sourced from a tox.toml file.

    This is experimental API! Expect things to be broken.
    """

    FILENAME = "tox.toml"


# TODO: Section model is way too configparser precific for this to work easily.
# class PyProjectToml(TomlSource):
#     """Configuration sourced from a pyproject.toml file.

#     This is experimental API! Expect things to be broken.
#     """

#     FILENAME = "pyproject.toml"
#     CORE_SECTION = IniSection("tool", "tox")
