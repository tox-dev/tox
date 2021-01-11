from collections import OrderedDict, defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Sequence

from tox.config.loader.api import Loader, Override, OverrideMap
from tox.config.source import Source

from .sets import CoreConfigSet, EnvConfigSet


class Config:
    def __init__(
        self,
        config_source: Source,
        overrides: List[Override],
        root: Path,
        pos_args: Optional[Sequence[str]],
        work_dir: Path,
    ) -> None:
        self.pos_args = pos_args
        self.work_dir = work_dir
        self._root = root

        self._overrides: OverrideMap = defaultdict(list)
        for override in overrides:
            self._overrides[override.namespace].append(override)

        self._src = config_source
        self._env_to_set: Dict[str, EnvConfigSet] = OrderedDict()
        self._core_set: Optional[CoreConfigSet] = None
        self.register_config_set: Callable[[str, EnvConfigSet], Any] = lambda n, e: None

    @property
    def core(self) -> CoreConfigSet:
        if self._core_set is not None:
            return self._core_set
        core = CoreConfigSet(self, self._root)
        for loader in self._src.get_core(self._overrides):
            core.loaders.append(loader)

        from tox.plugin.manager import MANAGER

        MANAGER.tox_add_core_config(core)
        self._core_set = core
        return core

    def get_env(
        self, item: str, package: bool = False, loaders: Optional[Sequence[Loader[Any]]] = None
    ) -> EnvConfigSet:
        try:
            return self._env_to_set[item]
        except KeyError:
            env = EnvConfigSet(self, item)
            self._env_to_set[item] = env
            if loaders is not None:
                env.loaders.extend(loaders)
            for loader in self._src.get_env_loaders(item, self._overrides, package, env):
                env.loaders.append(loader)
            # whenever we load a new configuration we need build a tox environment which process defines the valid
            # configuration values
            self.register_config_set(item, env)
            return env

    def __iter__(self) -> Iterator[str]:
        return self._src.envs(self.core)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(config_source={self._src!r})"

    def __contains__(self, item: str) -> bool:
        return any(name for name in self if name == item)
