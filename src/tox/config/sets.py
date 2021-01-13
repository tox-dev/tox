from collections import OrderedDict
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
        self._keys: Dict[str, None] = OrderedDict()

    def add_config(
        self,
        keys: Union[str, Sequence[str]],
        of_type: Type[V],
        default: Union[Callable[["Config", Optional[str]], V], V],
        desc: str,
        post_process: Optional[Callable[[V, "Config"], V]] = None,
        overwrite: bool = False,
    ) -> ConfigDynamicDefinition[V]:
        """
        Add configuration value.
        """
        keys_ = self._make_keys(keys)
        definition = ConfigDynamicDefinition(keys_, desc, self._name, of_type, default, post_process)
        result = self._add_conf(keys_, definition)
        return cast(ConfigDynamicDefinition[V], result)

    def add_constant(self, keys: Union[str, Sequence[str]], desc: str, value: V) -> ConfigConstantDefinition[V]:
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
            for key in keys:
                self._defined[key] = definition
        return definition

    def __getitem__(self, item: str) -> Any:
        return self.load(item)

    def load(self, item: str, chain: Optional[List[str]] = None) -> Any:
        config_definition = self._defined[item]
        if chain is None:
            chain = []
        if item in chain:
            raise ValueError(f"circular chain detected {', '.join(chain[chain.index(item):])}")
        chain.append(item)
        return config_definition(self._conf, item, self.loaders, chain)

    def __repr__(self) -> str:
        values = (v for v in (f"name={self._name!r}" if self._name else "", f"loaders={self.loaders!r}") if v)
        return f"{self.__class__.__name__}({', '.join(values)})"

    def __iter__(self) -> Iterator[str]:
        return iter(self._keys.keys())

    def unused(self) -> List[str]:
        """Return a list of keys present in the config source but not used"""
        found: Set[str] = set()
        for loader in self.loaders:
            found.update(loader.found_keys())
        found -= self._defined.keys()
        return list(sorted(found))


class CoreConfigSet(ConfigSet):
    def __init__(self, conf: "Config", root: Path) -> None:
        super().__init__(conf, name=None)
        self.add_config(
            keys=["tox_root", "toxinidir"],
            of_type=Path,
            default=root,
            desc="the root directory (where the configuration file is found)",
        )
        work_dir_builder = (
            lambda conf, _: (conf.work_dir if conf.work_dir is not None else cast(Path, self["tox_root"])) / ".tox4"
        )
        self.add_config(
            keys=["work_dir", "toxworkdir"],
            of_type=Path,
            # here we pin to .tox4 to be able to use in parallel with v3 until final release
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
    def __init__(self, conf: "Config", name: Optional[str]):
        super().__init__(conf, name=name)
        self.default_set_env_loader: Callable[[], Mapping[str, str]] = lambda: {}

        def set_env_post_process(values: SetEnv, config: "Config") -> SetEnv:
            values.update(self.default_set_env_loader())
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
