"""
Group together configuration values that belong together (such as base tox configuration, tox environment configs)
"""
from abc import ABC, abstractmethod
from collections import OrderedDict
from copy import deepcopy
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generic,
    Iterable,
    Iterator,
    Optional,
    Sequence,
    Set,
    Type,
    TypeVar,
    Union,
    cast,
)

from tox.config.source.api import Loader

if TYPE_CHECKING:
    from tox.config.main import Config  # pragma: no cover


T = TypeVar("T")
V = TypeVar("V")


class ConfigDefinition(ABC, Generic[T]):
    """Abstract base class for configuration definitions"""

    def __init__(self, keys: Iterable[str], desc: str) -> None:
        self.keys = keys
        self.desc = desc

    @abstractmethod
    def __call__(self, src: Loader[T], conf: "Config") -> T:
        raise NotImplementedError


class ConfigConstantDefinition(ConfigDefinition[T]):
    """A configuration definition whose value is defined upfront (such as the tox environment name)"""

    def __init__(self, keys: Iterable[str], desc: str, value: Union[Callable[[], T], T]) -> None:
        super().__init__(keys, desc)
        self.value = value

    def __call__(self, src: Loader[T], conf: "Config") -> T:
        if callable(self.value):
            value = self.value()
        else:
            value = self.value
        return value


_PLACE_HOLDER = object()


class ConfigDynamicDefinition(ConfigDefinition[T]):
    """A configuration definition that comes from a source (such as in memory, an ini file, a toml file, etc.)"""

    def __init__(
        self,
        keys: Iterable[str],
        of_type: Type[T],
        default: T,
        desc: str,
        post_process: Optional[Callable[[T, "Config"], T]] = None,
    ) -> None:
        super().__init__(keys, desc)
        self.of_type = of_type
        self.default = default
        self.post_process = post_process
        self._cache: Union[object, T] = _PLACE_HOLDER

    def __call__(self, src: Loader[T], conf: "Config") -> T:
        if self._cache is _PLACE_HOLDER:
            for key in self.keys:
                override = next((o for o in conf.overrides if o.namespace == src.namespace and o.key == key), None)
                if override is not None:
                    from tox.config.source.ini.convert import StrConvert

                    value = StrConvert().to(override.value, self.of_type)
                    break
            else:
                for key in self.keys:
                    try:
                        value = src.load(key, self.of_type, conf)
                    except KeyError:
                        continue
                    break
                else:
                    value = self.default(conf, src.name) if callable(self.default) else self.default
            if self.post_process is not None:
                self.post_process(value, conf)  # noqa
            self._cache = value
        return cast(T, self._cache)

    def __deepcopy__(self, memo: Dict[int, "ConfigDynamicDefinition[T]"]) -> "ConfigDynamicDefinition[T]":
        # we should not copy the place holder as our checks would break
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            if k != "_cache" and v is _PLACE_HOLDER:
                value = deepcopy(v, memo=memo)  # noqa
            else:
                value = v
            setattr(result, k, value)
        return cast(ConfigDynamicDefinition[T], result)

    def __repr__(self) -> str:
        values = ((k, v) for k, v in vars(self).items() if k != "post_process" and v is not None)
        return f"{type(self).__name__}({', '.join('{}={}'.format(k, v) for k,v in values)})"


class ConfigSet:
    """A set of configuration that belong together (such as a tox environment settings, core tox settings)"""

    def __init__(self, raw: Loader[Any], conf: "Config"):
        self._raw = raw
        self._defined: Dict[str, ConfigDefinition[Any]] = {}
        self._conf = conf
        self._keys: Dict[str, None] = OrderedDict()
        self._raw.setup_with_conf(self)

    def add_config(
        self,
        keys: Union[str, Sequence[str]],
        of_type: Type[V],
        default: Any,
        desc: str,
        post_process: Optional[Callable[[V, "Config"], V]] = None,
        overwrite: bool = False,
    ) -> None:
        """
        Add configuration value.
        """
        keys_ = self._make_keys(keys)
        for key in keys_:
            if key in self._defined and overwrite is False:
                # already added
                return
        definition = ConfigDynamicDefinition(keys_, of_type, default, desc, post_process)
        self._add_conf(keys_, definition)

    def add_constant(self, keys: Sequence[str], desc: str, value: V) -> None:
        keys_ = self._make_keys(keys)
        definition = ConfigConstantDefinition(keys_, desc, value)
        self._add_conf(keys, definition)

    def make_package_conf(self) -> None:
        self._raw.make_package_conf()

    @staticmethod
    def _make_keys(keys: Union[str, Sequence[str]]) -> Sequence[str]:
        return (keys,) if isinstance(keys, str) else keys

    def _add_conf(self, keys: Union[str, Sequence[str]], definition: ConfigDefinition[V]) -> None:
        self._keys[keys[0]] = None
        for key in keys:
            self._defined[key] = definition

    @property
    def name(self) -> Optional[str]:
        return self._raw.name

    def __getitem__(self, item: str) -> Any:
        config_definition = self._defined[item]
        return config_definition(self._raw, self._conf)

    def __repr__(self) -> str:
        return "{}(raw={!r}, conf={!r})".format(type(self).__name__, self._raw, self._conf)

    def __iter__(self) -> Iterator[str]:
        return iter(self._keys.keys())

    def unused(self) -> Set[str]:
        """Return a list of keys present in the config source but not used"""
        return self._raw.found_keys() - set(self._defined.keys())
