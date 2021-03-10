from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Type,
    TypeVar,
    Union,
    cast,
)

from .of_type import ConfigConstantDefinition, ConfigDefinition, ConfigDynamicDefinition
from .set_env import SetEnv
from .types import EnvList

if TYPE_CHECKING:
    from tox.config.loader.api import Loader
    from tox.config.main import Config

V = TypeVar("V")


class ConfigSet:
    """A set of configuration that belong together (such as a tox environment settings, core tox settings)"""

    def __init__(self, conf: "Config", name: Optional[str]):
        self._name = name
        self._conf = conf
        self.loaders: List[Loader[Any]] = []
        self._defined: Dict[str, ConfigDefinition[Any]] = {}
        self._keys: Dict[str, None] = {}
        self._alias: Dict[str, str] = {}

    def add_config(
        self,
        keys: Union[str, Sequence[str]],
        of_type: Type[V],
        default: Union[Callable[["Config", Optional[str]], V], V],
        desc: str,
        post_process: Optional[Callable[[V], V]] = None,
        kwargs: Optional[Mapping[str, Any]] = None,
    ) -> ConfigDynamicDefinition[V]:
        """
        Add configuration value.

        :param keys: the keys under what to register the config (first is primary key)
        :param of_type: the type of the config value
        :param default: the default value of the config value
        :param desc: a help message describing the configuration
        :param post_process: a callback to post-process the configuration value after it has been loaded
        :param kwargs: additional arguments to pass to the configuration type at construction time
        :return: the new dynamic config definition
        """
        keys_ = self._make_keys(keys)
        definition = ConfigDynamicDefinition(keys_, desc, self._name, of_type, default, post_process, kwargs)
        result = self._add_conf(keys_, definition)
        return cast(ConfigDynamicDefinition[V], result)

    def add_constant(self, keys: Union[str, Sequence[str]], desc: str, value: V) -> ConfigConstantDefinition[V]:
        """
        Add a constant value.

        :param keys: the keys under what to register the config (first is primary key)
        :param desc: a help message describing the configuration
        :param value: the config value to use
        :return: the new constant config value
        """
        keys_ = self._make_keys(keys)
        definition = ConfigConstantDefinition(keys_, desc, self._name, value)
        result = self._add_conf(keys_, definition)
        return cast(ConfigConstantDefinition[V], result)

    @staticmethod
    def _make_keys(keys: Union[str, Sequence[str]]) -> Sequence[str]:
        return (keys,) if isinstance(keys, str) else keys

    def _add_conf(self, keys: Sequence[str], definition: ConfigDefinition[V]) -> ConfigDefinition[V]:
        key = keys[0]
        if key in self._defined:
            earlier = self._defined[key]
            # core definitions may be defined multiple times as long as all their options match, first defined wins
            if self._name is None and definition == earlier:
                definition = earlier
            else:
                raise ValueError(f"config {key} already defined")
        else:
            self._keys[key] = None
            for item in keys:
                self._alias[item] = key
            for key in keys:
                self._defined[key] = definition
        return definition

    def __getitem__(self, item: str) -> Any:
        """
        Get the config value for a given key (will materialize in case of dynamic config).

        :param item: the config key
        :return: the configuration value
        """
        return self.load(item)

    def load(self, item: str, chain: Optional[List[str]] = None) -> Any:
        """
        Get the config value for a given key (will materialize in case of dynamic config).

        :param item: the config key
        :param chain: a chain of configuration keys already loaded for this load operation (used to detect circles)
        :return: the configuration value
        """
        config_definition = self._defined[item]
        if chain is None:
            chain = []
        env_name = "tox" if self._name is None else f"testenv:{self._name}"
        key = f"{env_name}.{item}"
        if key in chain:
            raise ValueError(f"circular chain detected {', '.join(chain[chain.index(key):])}")
        chain.append(key)
        return config_definition(self._conf, item, self.loaders, chain)

    def __repr__(self) -> str:
        values = (v for v in (f"name={self._name!r}" if self._name else "", f"loaders={self.loaders!r}") if v)
        return f"{self.__class__.__name__}({', '.join(values)})"

    def __iter__(self) -> Iterator[str]:
        """:return: iterate through the defined config keys (primary keys used)"""
        return iter(self._keys.keys())

    def __contains__(self, item: str) -> bool:
        """
        Check if a configuration key is within the config set.

        :param item: the configuration value
        :return: a boolean indicating the truthiness of the statement
        """
        return item in self._alias

    def unused(self) -> List[str]:
        """:return: Return a list of keys present in the config source but not used"""
        found: Set[str] = set()
        # keys within loaders (only if the loader is not a parent too)
        parents = {id(i.parent) for i in self.loaders if i.parent is not None}
        for loader in self.loaders:
            if id(loader) not in parents:
                found.update(loader.found_keys())
        found -= self._defined.keys()
        return sorted(found)

    def primary_key(self, key: str) -> str:
        """
        Get the primary key for a config key.

        :param key: the config key
        :return: the key that's considered the primary for the input key
        """
        return self._alias[key]


class CoreConfigSet(ConfigSet):
    """Configuration set for the core tox config"""

    def __init__(self, conf: "Config", root: Path) -> None:
        super().__init__(conf, name=None)
        self.add_config(
            keys=["tox_root", "toxinidir"],
            of_type=Path,
            default=root,
            desc="the root directory (where the configuration file is found)",
        )

        def work_dir_builder(conf: "Config", env_name: Optional[str]) -> Path:  # noqa
            # here we pin to .tox/4 to be able to use in parallel with v3 until final release
            return (conf.work_dir if conf.work_dir is not None else cast(Path, self["tox_root"])) / ".tox" / "4"

        self.add_config(
            keys=["work_dir", "toxworkdir"],
            of_type=Path,
            default=work_dir_builder,
            desc="working directory",
        )
        self.add_config(
            keys=["temp_dir"],
            of_type=Path,
            default=lambda conf, _: cast(Path, self["tox_root"]) / ".temp",
            desc="temporary directory cleaned at start",
        )
        self.add_config(
            keys=["env_list", "envlist"],
            of_type=EnvList,
            default=EnvList([]),
            desc="define environments to automatically run",
        )


class EnvConfigSet(ConfigSet):
    """Configuration set for a tox environment"""

    def __init__(self, conf: "Config", name: Optional[str]):
        super().__init__(conf, name=name)
        self.default_set_env_loader: Callable[[], Mapping[str, str]] = lambda: {}

        def set_env_post_process(values: SetEnv) -> SetEnv:
            values.update_if_not_present(self.default_set_env_loader())
            return values

        self.add_config(
            keys=["set_env", "setenv"],
            of_type=SetEnv,
            default=SetEnv(""),
            desc="environment variables to set when running commands in the tox environment",
            post_process=set_env_post_process,
        )

    @property
    def name(self) -> str:
        return self._name  # type: ignore


__all__ = (
    "ConfigSet",
    "CoreConfigSet",
    "EnvConfigSet",
)
