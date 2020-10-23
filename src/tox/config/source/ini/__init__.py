"""Load """
from configparser import ConfigParser, SectionProxy
from copy import deepcopy
from itertools import chain
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Set

from tox.config.main import Config
from tox.config.sets import ConfigSet
from tox.config.source.api import Loader, Source
from tox.config.source.ini.convert import StrConvert
from tox.config.source.ini.factor import filter_for_env, find_envs
from tox.config.source.ini.replace import BASE_TEST_ENV, CORE_PREFIX, replace

TEST_ENV_PREFIX = f"{BASE_TEST_ENV}:"


class IniLoader(StrConvert, Loader[str]):
    """Load configuration from an ini section (ini file is a string to string dictionary)"""

    def __init__(
        self,
        section: Optional[SectionProxy],
        src: "ToxIni",
        name: Optional[str],
        default_base: List["IniLoader"],
        section_loader: Callable[[str], Optional[SectionProxy]],
        namespace: str,
    ) -> None:
        super().__init__(name, namespace)
        self._section: Optional[SectionProxy] = section
        self._src: ToxIni = src
        self._default_base = default_base
        self._base: List[IniLoader] = []
        self._section_loader = section_loader

    def __deepcopy__(self, memo: Any) -> "IniLoader":
        # python < 3.7 cannot copy config parser
        result: IniLoader = self.__class__.__new__(self.__class__)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            if k != "_section":
                value = deepcopy(v, memo=memo)  # noqa
            else:
                value = v
            setattr(result, k, value)
        return result

    def setup_with_conf(self, conf: ConfigSet) -> None:
        if self.name is None:
            return  # no inheritance for the base tox environment
        src = self._src

        class IniLoaderFromKey(IniLoader):
            def __init__(self, key: str) -> None:  # noqa
                loader = src[key]
                self.__dict__ = loader.__dict__

        # allow environment inheritance
        conf.add_config(
            keys="base",
            of_type=List[IniLoaderFromKey],
            default=self._default_base,
            desc="inherit missing keys from these sections",
        )
        self._base = conf["base"]

    def make_package_conf(self) -> None:
        """no inheritance please if this is a packaging env"""
        self._base = []

    def __repr__(self) -> str:
        return "{}(section={}, src={!r})".format(
            type(self).__name__,
            self._section.name if self._section else self.name,
            self._src,
        )

    def _load_raw(self, key: str, conf: Optional[Config], as_name: Optional[str] = None) -> str:
        for candidate in self.loaders:
            if as_name is None and candidate.name == "":
                as_name = self.name
            try:
                return candidate._load_raw_from(as_name, conf, key)
            except KeyError:
                continue
        else:
            raise KeyError

    def _load_raw_from(self, as_name: Optional[str], conf: Optional["Config"], key: str) -> str:
        if as_name is None:
            as_name = self.name
        if self._section is None:
            raise KeyError(key)
        value = self._section[key]
        collapsed_newlines = value.replace("\\\r", "").replace("\\\n", "")  # collapse explicit line splits
        replace_executed = replace(collapsed_newlines, conf, as_name, self._section_loader)  # do replacements
        factor_selected = filter_for_env(replace_executed, as_name)  # select matching factors
        # extend factors
        return factor_selected

    def get_value(self, section: str, key: str) -> str:
        section_proxy = self._section_loader(section)
        if section_proxy is None:
            raise KeyError(section)
        return section_proxy[key]

    @property
    def loaders(self) -> Iterator["IniLoader"]:
        yield self
        yield from self._base

    def found_keys(self) -> Set[str]:
        result: Set[str] = set()
        for candidate in self.loaders:
            if candidate._section is not None:
                result.update(candidate._section.keys())
        return result

    @property
    def section_name(self) -> Optional[str]:
        if self._section is None:
            return None
        return self._section.name


class ToxIni(Source):
    """Configuration sourced from a ini file (such as tox.ini)"""

    def __init__(self, path: Path) -> None:
        self._path = path

        self._parser = ConfigParser()
        with self._path.open() as file_handler:
            self._parser.read_file(file_handler)
        core = IniLoader(
            section=self._get_section(CORE_PREFIX),
            src=self,
            name=None,
            default_base=[],
            section_loader=self._get_section,
            namespace=CORE_PREFIX,
        )
        super().__init__(core=core)
        self._envs: Dict[str, IniLoader] = {}

    def _get_section(self, key: str) -> Optional[SectionProxy]:
        if self._parser.has_section(key):
            return self._parser[key]
        return None

    def __deepcopy__(self, memo: Dict[int, Any]) -> "ToxIni":
        # python < 3.7 cannot copy config parser
        result: ToxIni = self.__class__.__new__(self.__class__)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            if k != "_parser":
                value = deepcopy(v, memo=memo)  # noqa
            else:
                value = v
            setattr(result, k, value)
        return result

    @property
    def tox_root(self) -> Path:
        return self._path.parent.absolute()

    def envs(self, core_config: ConfigSet) -> Iterator[str]:
        seen = set()
        for name in self._discover_tox_envs(core_config):
            if name not in seen:
                seen.add(name)
                yield name

    def __getitem__(self, item: str) -> "IniLoader":
        key = f"{TEST_ENV_PREFIX}{item}"
        return self.get_section(key, item)

    def get_section(self, item: str, name: str) -> "IniLoader":
        try:
            return self._envs[item]
        except KeyError:
            base = [] if item == BASE_TEST_ENV else [self.get_section(BASE_TEST_ENV, "")]
            loader = IniLoader(
                section=self._get_section(item),
                src=self,
                name=name,
                default_base=base,
                section_loader=self._get_section,
                namespace=item,
            )
            self._envs[item] = loader
            return loader

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
        for key in self._parser[section]:
            value = self._parser[section].get(key)
            if value:
                for env in find_envs(value):
                    if env not in known_factors:
                        yield env

    def __repr__(self) -> str:
        return f"{type(self).__name__}(path={self._path})"


__all__ = (
    "ToxIni",
    "IniLoader",
)
