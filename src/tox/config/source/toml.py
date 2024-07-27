"""Support for TOML config sources.

This is experimental API! Expect things to be broken.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import chain
from typing import TYPE_CHECKING, Any, Iterable, Iterator

import tomllib

from tox.config.loader.ini.factor import find_envs
from tox.config.loader.memory import MemoryLoader

from .api import Source
from .toml_section import BASE_TEST_ENV, CORE, PKG_ENV_PREFIX, TEST_ENV_PREFIX, TEST_ENV_ROOT, TomlSection

if TYPE_CHECKING:
    from pathlib import Path

    from tox.config.loader.api import OverrideMap
    from tox.config.loader.section import Section
    from tox.config.sets import ConfigSet


def _extract_section(raw: dict[str, Any], section: TomlSection) -> Any:
    """Extract section from TOML decoded data."""
    result = raw
    for key in chain(section.prefix, (section.name,)):
        if key in result:
            result = result[key]
        else:
            return None
    return result


class TomlSource(Source):
    """Configuration sourced from a toml file (such as tox.toml).

    This is experimental API! Expect things to be broken.
    """

    CORE_SECTION = CORE
    ROOT_KEY: str | None = None

    def __init__(self, path: Path, content: str | None = None) -> None:
        super().__init__(path)
        if content is None:
            if not path.exists():
                msg = f"Path {path} does not exist."
                raise ValueError(msg)
            content = path.read_text()
        data = tomllib.loads(content)
        if self.ROOT_KEY:
            if self.ROOT_KEY not in data:
                msg = f"Section {self.ROOT_KEY} not found in {path}."
                raise ValueError(msg)
            data = data[self.ROOT_KEY]
        self._raw = data
        self._section_mapping: defaultdict[str, list[str]] = defaultdict(list)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(path={self.path})"

    def transform_section(self, section: Section) -> Section:
        return TomlSection(section.prefix, section.name)

    def get_loader(self, section: TomlSection, override_map: OverrideMap) -> MemoryLoader | None:
        result = _extract_section(self._raw, section)
        if result is None:
            return None

        return MemoryLoader(
            result,
            section=section,
            overrides=override_map.get(section.key, []),
        )

    def get_base_sections(self, base: list[str], in_section: Section) -> Iterator[Section]:  # noqa: PLR6301
        for a_base in base:
            yield TomlSection(in_section.prefix, a_base)

    def sections(self) -> Iterator[TomlSection]:
        # TODO: just return core section and any `tox.env.XXX` sections which exist directly.
        for key in self._raw:
            section = TomlSection.from_key(key)
            yield section
            if section == self.CORE_SECTION:
                test_env_data = _extract_section(self._raw, TEST_ENV_ROOT)
                for env_name in test_env_data or {}:
                    yield TomlSection(TEST_ENV_PREFIX, env_name)

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

    def _discover_from_section(self, section: TomlSection, known_factors: set[str]) -> Iterator[str]:
        section_data = _extract_section(self._raw, section)
        for value in (section_data or {}).values():
            if isinstance(value, bool):
                # It's not a value with env definition.
                continue
            # XXX: We munch the value to multiline string to parse it by the library utils.
            merged_value = "\n".join(str(v) for v in tuple(value))
            for env in find_envs(merged_value):
                if set(env.split("-")) - known_factors:
                    yield env

    def get_tox_env_section(self, item: str) -> tuple[TomlSection, list[str], list[str]]:  # noqa: PLR6301
        return TomlSection.test_env(item), [BASE_TEST_ENV], [PKG_ENV_PREFIX]

    def get_core_section(self) -> TomlSection:
        return self.CORE_SECTION


class ToxToml(TomlSource):
    """Configuration sourced from a tox.toml file.

    This is experimental API! Expect things to be broken.
    """

    FILENAME = "tox.toml"


class PyProjectToml(TomlSource):
    """Configuration sourced from a pyproject.toml file.

    This is experimental API! Expect things to be broken.
    """

    FILENAME = "pyproject.toml"
    ROOT_KEY = "tool"

    def __init__(self, path: Path, content: str | None = None) -> None:
        super().__init__(path, content)
        core_data = _extract_section(self._raw, self.CORE_SECTION)
        if core_data is not None and tuple(core_data.keys()) == ("legacy_tox_ini",):
            msg = "pyproject.toml is in the legacy mode."
            raise ValueError(msg)
