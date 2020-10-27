from collections import OrderedDict
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterator, List

from tox.plugin.impl import impl

from .override import Override
from .sets import ConfigSet
from .source.api import Source

if TYPE_CHECKING:
    from tox.config.cli.parser import ToxParser


@impl
def tox_add_option(parser: "ToxParser") -> None:
    parser.add_argument(
        "-o",
        "--override",
        action="append",
        type=Override,
        default=[],
        dest="override",
        help="list of configuration override(s)",
    )


class Config:
    def __init__(self, config_source: Source, overrides: List[Override]) -> None:
        self.overrides = overrides
        self._src = config_source
        self.core = self._setup_core()
        self._env_names = list(self._src.envs(self.core))
        self._envs: Dict[str, ConfigSet] = OrderedDict()
        self.register_config_set: Callable[[str], Any] = lambda x: None

    def _setup_core(self) -> ConfigSet:
        core = ConfigSet(self._src.core, self)
        core.add_config(
            keys=["tox_root", "toxinidir"],
            of_type=Path,
            default=self._src.tox_root,
            desc="the root directory (where the configuration file is found)",
        )
        from tox.plugin.manager import MANAGER

        MANAGER.tox_add_core_config(core)
        return core

    def __getitem__(self, item: str) -> ConfigSet:
        try:
            return self._envs[item]
        except KeyError:
            env = ConfigSet(self._src[item], self)
            self._envs[item] = env
            # whenever we load a new configuration we need build a tox environment which process defines the valid
            # configuration values
            self.register_config_set(item)
            return env

    def __iter__(self) -> Iterator[str]:
        return iter(self._env_names)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(config_source={self._src!r})"

    def __contains__(self, item: str) -> bool:
        return item in self._env_names
