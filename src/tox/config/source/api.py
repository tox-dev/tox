import sys
from abc import ABC, abstractmethod
from collections import OrderedDict
from enum import Enum
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    Iterator,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from tox.execute.request import shell_cmd

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal  # noqa

if TYPE_CHECKING:
    from tox.config.main import Config
    from tox.config.sets import ConfigSet
_NO_MAPPING = object()


class Command:
    def __init__(self, args: List[str]) -> None:
        self.args = args

    def __repr__(self) -> str:
        return f"{type(self).__name__}(args={self.args!r})"

    def __eq__(self, other: Any) -> bool:
        return type(self) == type(other) and self.args == other.args

    def __ne__(self, other: Any) -> bool:
        return not (self == other)

    @property
    def shell(self) -> str:
        return shell_cmd(self.args)


class EnvList:
    def __init__(self, envs: Sequence[str]) -> None:
        self.envs = list(OrderedDict((e, None) for e in envs).keys())

    def __repr__(self) -> str:
        return "{}(envs={!r})".format(type(self).__name__, ",".join(self.envs))

    def __eq__(self, other: Any) -> bool:
        return type(self) == type(other) and self.envs == other.envs

    def __ne__(self, other: Any) -> bool:
        return not (self == other)

    def __iter__(self) -> Iterator[str]:
        return iter(self.envs)


T = TypeVar("T")
V = TypeVar("V")


class Convert(ABC, Generic[T]):
    """A class that converts a raw type to a given tox (python) type"""

    def to(self, raw: T, of_type: Type[V]) -> V:

        from_module = getattr(of_type, "__module__", None)
        if from_module in ("typing", "typing_extensions"):
            return self._to_typing(raw, of_type)
        elif issubclass(of_type, Path):
            return self.to_path(raw)  # type: ignore[return-value]
        elif issubclass(of_type, bool):
            return self.to_bool(raw)  # type: ignore[return-value]
        elif issubclass(of_type, Command):
            return self.to_command(raw)  # type: ignore[return-value]
        elif issubclass(of_type, EnvList):
            return self.to_env_list(raw)  # type: ignore[return-value]
        elif issubclass(of_type, str):
            return self.to_str(raw)  # type: ignore[return-value]
        elif issubclass(of_type, Enum):
            return cast(V, getattr(of_type, str(raw)))
        return of_type(raw)  # type: ignore[call-arg]

    def _to_typing(self, raw: T, of_type: Type[V]) -> V:
        origin = getattr(of_type, "__origin__", getattr(of_type, "__class__", None))
        if origin is not None:
            result: Any = _NO_MAPPING
            if origin in (list, List):
                entry_type = of_type.__args__[0]  # type: ignore[attr-defined]
                result = [self.to(i, entry_type) for i in self.to_list(raw)]
            elif origin in (set, Set):
                entry_type = of_type.__args__[0]  # type: ignore[attr-defined]
                result = {self.to(i, entry_type) for i in self.to_set(raw)}
            elif origin in (dict, Dict):
                key_type, value_type = of_type.__args__[0], of_type.__args__[1]  # type: ignore[attr-defined]
                result = OrderedDict((self.to(k, key_type), self.to(v, value_type)) for k, v in self.to_dict(raw))
            elif origin == Union:  # handle Optional values
                args: List[Type[Any]] = of_type.__args__  # type: ignore[attr-defined]
                none = type(None)
                if len(args) == 2 and none in args:
                    if isinstance(raw, str):
                        raw = raw.strip()  # type: ignore[assignment]
                    if not raw:
                        result = None
                    else:
                        new_type = next(i for i in args if i != none)  # noqa
                        result = self._to_typing(raw, new_type)
            elif origin == Literal or origin == type(Literal):
                if sys.version_info >= (3, 7):
                    choice = of_type.__args__
                else:
                    choice = of_type.__values__  # type: ignore[attr-defined]
                if raw not in choice:
                    raise ValueError(f"{raw} must be one of {choice}")
                result = raw
            if result is not _NO_MAPPING:
                return cast(V, result)
        raise TypeError(f"{raw} cannot cast to {of_type!r}")

    @staticmethod
    @abstractmethod
    def to_str(value: T) -> str:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def to_list(value: T) -> Iterator[T]:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def to_set(value: T) -> Iterator[T]:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def to_dict(value: T) -> Iterator[Tuple[T, T]]:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def to_path(value: T) -> Path:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def to_command(value: T) -> Command:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def to_env_list(value: T) -> EnvList:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def to_bool(value: T) -> bool:
        raise NotImplementedError


class Loader(Convert[T]):
    """Loader loads a configuration value and converts it."""

    def __init__(self, name: Optional[str], namespace: str) -> None:
        """
        Create a loader.

        :param name: name of this loader: ``None`` for core, otherwise the tox environment name
        :param name: the namespace under the name exists within the config
        """
        self.name = name
        self.namespace = namespace

    def load(self, key: str, of_type: Type[V], conf: Optional["Config"]) -> V:
        """
        Load a value.

        :param key: the key under it lives
        :param of_type: the type to convert to
        :param conf: the configuration object of this tox session (needed to manifest the value)
        :return: the converted type
        """
        raw = self._load_raw(key, conf)
        converted = self.to(raw, of_type)
        return converted

    @abstractmethod
    def setup_with_conf(self, conf: "ConfigSet") -> None:
        """Notifies the loader when the global configuration object has been constructed"""
        raise NotImplementedError

    def make_package_conf(self) -> None:
        """Notifies the loader that this is a package configuration."""

    @abstractmethod
    def _load_raw(self, key: str, conf: Optional["Config"]) -> T:
        """
        Load the raw object from the config store.

        :param key: the key under what we want the configuration
        :param conf: the global config object
        """
        raise NotImplementedError

    @abstractmethod
    def found_keys(self) -> Set[str]:
        """A list of configuration keys found within the configuration."""
        raise NotImplementedError


class Source(ABC):
    """
    Source is able to return a configuration value (for either the core or per environment source).
    """

    def __init__(self, core: Loader[Any]) -> None:
        self.core = core

    @abstractmethod
    def envs(self, core_conf: "ConfigSet") -> Iterator[str]:
        raise NotImplementedError

    @abstractmethod
    def __getitem__(self, item: str) -> Loader[Any]:
        raise NotImplementedError

    @property
    @abstractmethod
    def tox_root(self) -> Path:
        raise NotImplementedError
