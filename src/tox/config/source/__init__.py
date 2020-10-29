"""Sources."""
from abc import ABC, abstractmethod
from typing import Any, Iterator

from tox.config.loader.api import Loader, OverrideMap

from ..sets import ConfigSet, CoreConfigSet


class Source(ABC):
    """
    Source is able to return a configuration value (for either the core or per environment source).
    """

    @abstractmethod
    def get_core(self, override_map: OverrideMap) -> Iterator[Loader[Any]]:
        """Return the core loader from this source."""
        raise NotImplementedError

    @abstractmethod
    def get_env_loaders(
        self, env_name: str, override_map: OverrideMap, package: bool, conf: ConfigSet
    ) -> Iterator[Loader[Any]]:
        """Return the load for this environment."""
        raise NotImplementedError

    @abstractmethod
    def envs(self, core_conf: "CoreConfigSet") -> Iterator[str]:
        """Return a list of environments defined within this source"""
        raise NotImplementedError
