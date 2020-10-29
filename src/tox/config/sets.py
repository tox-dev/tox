from collections import OrderedDict
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Set,
    Type,
    TypeVar,
    Union,
    cast,
)

from .of_type import ConfigConstantDefinition, ConfigDefinition, ConfigDynamicDefinition
from .types import EnvList

if TYPE_CHECKING:
    from tox.config.loader.api import Loader
    from tox.config.main import Config

V = TypeVar("V")


class ConfigSet:
    """A set of configuration that belong together (such as a tox environment settings, core tox settings)"""

    def __init__(self, conf: "Config", name: Optional[str]):
        self.name = name
        self._conf = conf
        self._loaders: List[Loader[Any]] = []
        self._defined: Dict[str, ConfigDefinition[Any]] = {}
        self._keys: Dict[str, None] = OrderedDict()

    def add_loader(self, loader: "Loader[Any]") -> None:
        self._loaders.append(loader)

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
        for key in keys_:
            if key in self._defined and overwrite is False:
                defined = self._defined[key]
                if isinstance(defined, ConfigDynamicDefinition):
                    return defined
                raise TypeError(f"{keys} already defined with differing type {type(defined).__name__}")
        definition = ConfigDynamicDefinition(keys_, desc, self.name, of_type, default, post_process)
        self._add_conf(keys_, definition)
        return definition

    def add_constant(self, keys: Sequence[str], desc: str, value: V) -> ConfigConstantDefinition[V]:
        keys_ = self._make_keys(keys)
        definition = ConfigConstantDefinition(keys_, desc, self.name, value)
        self._add_conf(keys, definition)
        return definition

    @staticmethod
    def _make_keys(keys: Union[str, Sequence[str]]) -> Sequence[str]:
        return (keys,) if isinstance(keys, str) else keys

    def _add_conf(self, keys: Union[str, Sequence[str]], definition: ConfigDefinition[V]) -> None:
        self._keys[keys[0]] = None
        for key in keys:
            self._defined[key] = definition

    def __getitem__(self, item: str) -> Any:
        config_definition = self._defined[item]
        return config_definition(self._conf, item, self._loaders)

    def __repr__(self) -> str:
        values = (v for v in (f"name={self.name!r}" if self.name else "", f"loaders={self._loaders!r}") if v)
        return f"{self.__class__.__name__}({', '.join(values)})"

    def __iter__(self) -> Iterator[str]:
        return iter(self._keys.keys())

    def unused(self) -> Set[str]:
        """Return a list of keys present in the config source but not used"""
        found = set()
        for loader in self._loaders:
            found.update(loader.found_keys())
        return found - set(self._defined.keys())


class CoreConfigSet(ConfigSet):
    def __init__(self, conf: "Config", root: Path) -> None:
        super().__init__(conf, name=None)
        self.add_config(
            keys=["tox_root", "toxinidir"],
            of_type=Path,
            default=root,
            desc="the root directory (where the configuration file is found)",
        )
        self.add_config(
            keys=["work_dir", "toxworkdir"],
            of_type=Path,
            # here we pin to .tox4 to be able to use in parallel with v3 until final release
            default=lambda conf, _: cast(Path, self["tox_root"]) / ".tox4",
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
        self.add_config(
            keys=["skip_missing_interpreters"],
            of_type=bool,
            default=True,
            desc="skip missing interpreters",
        )
