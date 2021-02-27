"""Load """
from abc import ABC
from configparser import ConfigParser
from itertools import chain
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Set

from tox.config.loader.ini.factor import find_envs

from ..loader.api import OverrideMap
from ..loader.ini import IniLoader
from ..loader.ini.replace import BASE_TEST_ENV
from ..sets import ConfigSet
from .api import Source

TEST_ENV_PREFIX = f"{BASE_TEST_ENV}:"


class IniSource(Source, ABC):
    """Configuration sourced from a ini file (such as tox.ini)"""

    CORE_PREFIX = "tox"

    def __init__(self, path: Path, content: Optional[str] = None) -> None:
        super().__init__(path)
        self._parser = ConfigParser()
        if content is None:
            if not path.exists():
                raise ValueError
            content = path.read_text()
        self._parser.read_string(content, str(path))
        self._envs: Dict[Optional[str], List[IniLoader]] = {}

    def get_core(self, override_map: OverrideMap) -> Iterator[IniLoader]:
        if None in self._envs:
            yield from self._envs[None]
            return
        core = []
        if self._parser.has_section(self.CORE_PREFIX):
            core.append(
                IniLoader(
                    section=self.CORE_PREFIX,
                    parser=self._parser,
                    overrides=override_map.get(self.CORE_PREFIX, []),
                    core_prefix=self.CORE_PREFIX,
                )
            )
        self._envs[None] = core
        yield from core

    def get_env_loaders(
        self, env_name: str, override_map: OverrideMap, package: bool, conf: ConfigSet
    ) -> Iterator[IniLoader]:
        section = f"{TEST_ENV_PREFIX}{env_name}"
        try:
            yield from self._envs[section]
        except KeyError:
            loaders: List[IniLoader] = []
            self._envs[section] = loaders
            loader: Optional[IniLoader] = None
            if self._parser.has_section(section):
                loader = IniLoader(
                    section=section,
                    parser=self._parser,
                    overrides=override_map.get(section, []),
                    core_prefix=self.CORE_PREFIX,
                )
                yield loader
                loaders.append(loader)

            if package is False:
                conf.add_config(  # base may be override within the testenv:py section
                    keys="base",
                    of_type=List[str],
                    desc="inherit missing keys from these sections",
                    default=[BASE_TEST_ENV],
                )
                for base in conf["base"]:
                    for section in (base, f"{TEST_ENV_PREFIX}{base}"):
                        if self._parser.has_section(section):
                            child = loader
                            loader = IniLoader(
                                section=section,
                                parser=self._parser,
                                overrides=override_map.get(section, []),
                                core_prefix=self.CORE_PREFIX,
                            )
                            if child is not None:
                                child.parent = loader
                            yield loader
                            loaders.append(loader)
                            break

    def envs(self, core_config: ConfigSet) -> Iterator[str]:
        seen = set()
        for name in self._discover_tox_envs(core_config):
            if name not in seen:
                seen.add(name)
                yield name

    def _discover_tox_envs(self, core_config: ConfigSet) -> Iterator[str]:
        explicit = list(core_config["env_list"])
        yield from explicit
        known_factors = None
        for section in self._parser.sections():
            if section.startswith(BASE_TEST_ENV):
                is_base_section = section == BASE_TEST_ENV
                name = BASE_TEST_ENV if is_base_section else section[len(TEST_ENV_PREFIX) :]
                if not is_base_section:
                    yield name
                if known_factors is None:
                    known_factors = set(chain.from_iterable(e.split("-") for e in explicit))
                yield from self._discover_from_section(section, known_factors)

    def _discover_from_section(self, section: str, known_factors: Set[str]) -> Iterator[str]:
        for value in self._parser[section].values():
            for env in find_envs(value):
                if env not in known_factors:
                    yield env

    def __repr__(self) -> str:
        return f"{type(self).__name__}(path={self.path})"


__all__ = ("IniSource",)
