"""
Group together configuration values that belong together (such as base tox configuration, tox environment configs)
"""
from abc import ABC, abstractmethod
from itertools import product
from typing import TYPE_CHECKING, Any, Callable, Generic, Iterable, List, Mapping, Optional, Type, TypeVar, Union, cast

from tox.config.loader.api import Loader

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
    def __call__(
        self,
        conf: "Config",  # noqa: U100
        loaders: List[Loader[T]],  # noqa: U100
        env_name: Optional[str],  # noqa: U100
        chain: Optional[List[str]],  # noqa: U100
    ) -> T:
        raise NotImplementedError

    def __eq__(self, o: Any) -> bool:
        return type(self) == type(o) and (self.keys, self.desc) == (o.keys, o.desc)

    def __ne__(self, o: Any) -> bool:
        return not (self == o)


class ConfigConstantDefinition(ConfigDefinition[T]):
    """A configuration definition whose value is defined upfront (such as the tox environment name)"""

    def __init__(
        self,
        keys: Iterable[str],
        desc: str,
        value: Union[Callable[[], T], T],
    ) -> None:
        super().__init__(keys, desc)
        self.value = value

    def __call__(
        self,
        conf: "Config",  # noqa: U100
        loaders: List[Loader[T]],  # noqa: U100
        env_name: Optional[str],  # noqa: U100
        chain: Optional[List[str]],  # noqa: U100
    ) -> T:
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
        of_type: Type[T],
        default: Union[Callable[["Config", Optional[str]], T], T],
        post_process: Optional[Callable[[T], T]] = None,
        kwargs: Optional[Mapping[str, Any]] = None,
    ) -> None:
        super().__init__(keys, desc)
        self.of_type = of_type
        self.default = default
        self.post_process = post_process
        self.kwargs: Mapping[str, Any] = {} if kwargs is None else kwargs
        self._cache: Union[object, T] = _PLACE_HOLDER

    def __call__(
        self, conf: "Config", loaders: List[Loader[T]], env_name: Optional[str], chain: Optional[List[str]]
    ) -> T:
        if chain is None:
            chain = []
        if self._cache is _PLACE_HOLDER:
            for key, loader in product(self.keys, loaders):
                chain_key = f"{loader.section_name}.{key}"
                if chain_key in chain:
                    raise ValueError(f"circular chain detected {', '.join(chain[chain.index(chain_key):])}")
                chain.append(chain_key)
                try:
                    value = loader.load(key, self.of_type, self.kwargs, conf, env_name, chain)
                except KeyError:
                    continue
                else:
                    break
                finally:
                    del chain[-1]
            else:
                value = self.default(conf, env_name) if callable(self.default) else self.default
            if self.post_process is not None:
                value = self.post_process(value)  # noqa
            self._cache = value
        return cast(T, self._cache)

    def __repr__(self) -> str:
        values = ((k, v) for k, v in vars(self).items() if k != "post_process" and v is not None)
        return f"{type(self).__name__}({', '.join(f'{k}={v}' for k, v in values)})"

    def __eq__(self, o: Any) -> bool:
        return (
            type(self) == type(o)
            and super().__eq__(o)
            and (self.of_type, self.default, self.post_process) == (o.of_type, o.default, o.post_process)
        )
