"""
Group together configuration values that belong together (such as base tox configuration, tox environment configs)
"""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable, Generic, Iterable, List, Optional, Type, TypeVar, Union, cast

from tox.config.loader.api import Loader

if TYPE_CHECKING:
    from tox.config.main import Config  # pragma: no cover


T = TypeVar("T")
V = TypeVar("V")


class ConfigDefinition(ABC, Generic[T]):
    """Abstract base class for configuration definitions"""

    def __init__(self, keys: Iterable[str], desc: str, env_name: Optional[str]) -> None:
        self.keys = keys
        self.desc = desc
        self.env_name = env_name

    @abstractmethod
    def __call__(self, conf: "Config", key: Optional[str], loaders: List[Loader[T]], chain: List[str]) -> T:
        raise NotImplementedError

    def __eq__(self, o: Any) -> bool:
        return type(self) == type(o) and (self.keys, self.desc, self.env_name) == (o.keys, o.desc, o.env_name)

    def __ne__(self, o: Any) -> bool:
        return not (self == o)


class ConfigConstantDefinition(ConfigDefinition[T]):
    """A configuration definition whose value is defined upfront (such as the tox environment name)"""

    def __init__(
        self,
        keys: Iterable[str],
        desc: str,
        env_name: Optional[str],
        value: Union[Callable[[], T], T],
    ) -> None:
        super().__init__(keys, desc, env_name)
        self.value = value

    def __call__(self, conf: "Config", name: Optional[str], loaders: List[Loader[T]], chain: List[str]) -> T:
        if callable(self.value):
            value = self.value()
        else:
            value = self.value
        return value

    def __eq__(self, o: Any) -> bool:
        return type(self) == type(o) and super().__eq__(o) and self.value == o.value


_PLACE_HOLDER = object()


class ConfigDynamicDefinition(ConfigDefinition[T]):
    """A configuration definition that comes from a source (such as in memory, an ini file, a toml file, etc.)"""

    def __init__(
        self,
        keys: Iterable[str],
        desc: str,
        env_name: Optional[str],
        of_type: Type[T],
        default: Union[Callable[["Config", Optional[str]], T], T],
        post_process: Optional[Callable[[T, "Config"], T]] = None,
    ) -> None:
        super().__init__(keys, desc, env_name)
        self.of_type = of_type
        self.default = default
        self.post_process = post_process
        self._cache: Union[object, T] = _PLACE_HOLDER

    def __call__(self, conf: "Config", name: Optional[str], loaders: List[Loader[T]], chain: List[str]) -> T:
        if self._cache is _PLACE_HOLDER:
            found = False
            for key in self.keys:
                for loader in loaders:
                    try:
                        value = loader.load(key, self.of_type, conf, self.env_name, chain)
                        found = True
                    except KeyError:
                        continue
                    break
                if found:
                    break
            else:
                value = self.default(conf, self.env_name) if callable(self.default) else self.default
            if self.post_process is not None:
                value = self.post_process(value, conf)  # noqa
            self._cache = value
        return cast(T, self._cache)

    def __repr__(self) -> str:
        values = ((k, v) for k, v in vars(self).items() if k != "post_process" and v is not None)
        return f"{type(self).__name__}({', '.join('{}={}'.format(k, v) for k,v in values)})"

    def __eq__(self, o: Any) -> bool:
        return (
            type(self) == type(o)
            and super().__eq__(o)
            and (self.of_type, self.default, self.post_process) == (o.of_type, o.default, o.post_process)
        )
