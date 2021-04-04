"""Sources."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterator

from tox.config.loader.api import Loader, OverrideMap

from ..sets import ConfigSet, CoreConfigSet


class Source(ABC):
    """
    Source is able to return a configuration value (for either the core or per environment source).
    """

    FILENAME = ""

    def __init__(self, path: Path) -> None:
        self.path: Path = path  #: the path to the configuration source

    @abstractmethod
    def get_core(self, override_map: OverrideMap) -> Iterator[Loader[Any]]:  # noqa: U100
        """
        Return a loader that loads the core configuration values.

        :param override_map: a list of overrides to apply
        :returns: the core loader from this source
        """
        raise NotImplementedError

    @abstractmethod
    def get_env_loaders(
        self, env_name: str, override_map: OverrideMap, package: bool, conf: ConfigSet  # noqa: U100
    ) -> Iterator[Loader[Any]]:
        """
        Return the load for this environment.

        :param env_name: the environment name
        :param override_map: a list of overrides to apply
        :param package: a flag indicating if this is a package environment, otherwise is of type run
        :param conf: the config set to use
        :returns: an iterable of loaders extracting config value from this source
        """
        raise NotImplementedError

    @abstractmethod
    def envs(self, core_conf: "CoreConfigSet") -> Iterator[str]:  # noqa: U100
        """
        :param core_conf: the core configuration set
        :returns: a list of environments defined within this source
        """
        raise NotImplementedError


__all__ = ("Source",)
