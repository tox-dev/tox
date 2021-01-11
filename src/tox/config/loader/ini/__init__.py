import inspect
from concurrent.futures import Future
from configparser import ConfigParser, SectionProxy
from contextlib import contextmanager
from typing import Generator, List, Optional, Set, Type, TypeVar

from tox.config.loader.api import Loader, Override
from tox.config.loader.ini.factor import filter_for_env
from tox.config.loader.ini.replace import replace
from tox.config.loader.str_convert import StrConvert
from tox.config.main import Config
from tox.config.set_env import SetEnv
from tox.report import HandledError

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
        collapsed_newlines = value.replace("\\\r\n", "").replace("\\\n", "")  # collapse explicit new-line escape
        if conf is None:  # conf is None when we're loading the global tox configuration file for the CLI
            factor_filtered = collapsed_newlines  # we don't support factor and replace functionality there
        else:
            factor_filtered = filter_for_env(collapsed_newlines, env_name)  # select matching factors
        return factor_filtered

    @contextmanager
    def build(
        self,
        future: "Future[V]",
        key: str,
        of_type: Type[V],
        conf: Optional["Config"],
        env_name: Optional[str],
        raw: str,
        chain: List[str],
    ) -> Generator[str, None, None]:
        delay_replace = inspect.isclass(of_type) and issubclass(of_type, SetEnv)

        def replacer(raw_: str, chain_: List[str]) -> str:
            if conf is None:
                replaced = raw_  # no replacement supported in the core section
            else:
                try:
                    replaced = replace(conf, env_name, self, raw_, chain_)  # do replacements
                except Exception as exception:
                    msg = f"replace failed in {'tox' if env_name is None else env_name}.{key} with {exception!r}"
                    raise HandledError(msg) from exception
            return replaced

        if not delay_replace:
            raw = replacer(raw, chain)
        yield raw
        if delay_replace:
            converted = future.result()
            if hasattr(converted, "replacer"):  # pragma: no branch
                converted.replacer = replacer  # type: ignore[attr-defined]

    def found_keys(self) -> Set[str]:
        return set(self._section.keys())

    def get_section(self, name: str) -> Optional[SectionProxy]:
        # needed for non tox environment replacements
        if self._parser.has_section(name):
            return self._parser[name]
        return None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(section={self._section}, overrides={self.overrides!r})"
