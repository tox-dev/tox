from configparser import ConfigParser, SectionProxy
from copy import deepcopy
from typing import Any, List, Optional, Set, TypeVar

from tox.config.loader.api import Loader, Override
from tox.config.loader.ini.factor import filter_for_env
from tox.config.loader.ini.replace import replace
from tox.config.loader.str_convert import StrConvert
from tox.config.main import Config

V = TypeVar("V")


class IniLoader(StrConvert, Loader[str]):
    """Load configuration from an ini section (ini file is a string to string dictionary)"""

    def __init__(
        self,
        section: str,
        parser: ConfigParser,
        overrides: List[Override],
    ) -> None:
        self._section: SectionProxy = parser[section]
        self._parser = parser
        super().__init__(overrides)

    def load_raw(self, key: str, conf: Optional[Config], env_name: Optional[str]) -> str:
        value = self._section[key]
        collapsed_newlines = value.replace("\\\r", "").replace("\\\n", "")  # collapse explicit line splits
        replace_executed = replace(collapsed_newlines, conf, env_name, self)  # do replacements
        factor_selected = filter_for_env(replace_executed, env_name)  # select matching factors
        # extend factors
        return factor_selected

    def found_keys(self) -> Set[str]:
        return set(self._section.keys())

    def get_section(self, name: str) -> Optional[SectionProxy]:
        # needed for non tox environment replacements
        if self._parser.has_section(name):
            return self._parser[name]
        return None

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

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(section={self._section}, overrides={self.overrides!r})"
