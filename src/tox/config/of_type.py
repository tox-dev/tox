"""Group together configuration values (such as base tox configuration, tox environment configs)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import TYPE_CHECKING, Generic, TypeVar, cast

from tox.util.typing_compat import override

from .loader.api import ConfigLoadArgs, Loader
from .types import CircularChainError

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from types import UnionType

    from .loader.convert import Factory
    from .main import Config  # pragma: no cover  # setup not built by tests


T = TypeVar("T")
V = TypeVar("V")


class ConfigDefinition(ABC, Generic[T]):  # ruff:ignore[eq-without-hash]  # mutable value type
    """Abstract base class for configuration definitions.

    :param keys: the configuration keys, the first one is the name, the others are aliases
    :param desc: the help text describing the configuration

    """

    def __init__(self, keys: Iterable[str], desc: str) -> None:
        self.keys = keys
        self.desc = desc

    @abstractmethod
    def __call__(self, conf: Config, loaders: list[Loader[T]], args: ConfigLoadArgs) -> T:
        raise NotImplementedError

    @override
    def __eq__(self, o: object) -> bool:
        if not isinstance(o, ConfigDefinition):
            return NotImplemented
        return (self.keys, self.desc) == (o.keys, o.desc)

    @override
    def __ne__(self, o: object) -> bool:
        return not (self == o)

    @abstractmethod
    def overwrite(self, value: T) -> None:
        """Force the configuration to the given value, replacing any constant or already loaded one.

        :param value: the new value

        """
        raise NotImplementedError


class ConfigConstantDefinition(ConfigDefinition[T]):  # ruff:ignore[eq-without-hash]  # mutable value type
    """A configuration definition whose value is defined upfront (such as the tox environment name).

    :param keys: the configuration keys, the first one is the name, the others are aliases
    :param desc: the help text describing the configuration
    :param value: the value the configuration is fixed to

    """

    def __init__(
        self,
        keys: Iterable[str],
        desc: str,
        value: Callable[[], T] | T,
    ) -> None:
        super().__init__(keys, desc)
        self.value = value

    @override
    def __call__(
        self,
        conf: Config,
        loaders: list[Loader[T]],
        args: ConfigLoadArgs,
    ) -> T:
        if callable(self.value):
            return cast("Callable[[], T]", self.value)()
        return self.value

    @override
    def __eq__(self, o: object) -> bool:
        if not isinstance(o, ConfigConstantDefinition):
            return NotImplemented
        return super().__eq__(o) and self.value == o.value

    @override
    def __repr__(self) -> str:
        values = ((k, v) for k, v in self.__dict__.items() if v is not None)
        return f"{type(self).__name__}({', '.join(f'{k}={v}' for k, v in values)})"

    @override
    def overwrite(self, value: T) -> None:
        self.value = value


class ConfigDynamicDefinition(ConfigDefinition[T]):  # ruff:ignore[eq-without-hash]  # mutable value type
    """A configuration definition that comes from a source (such as in memory, an ini file, a toml file, etc.).

    :param keys: the configuration keys, the first one is the name, the others are aliases
    :param desc: the help text describing the configuration
    :param of_type: the type the loaded value is converted to
    :param default: the value, or a callable computing it, used when the configuration is not set
    :param post_process: a callable applied to the converted value
    :param factory: the callable that builds the objects of the type, for container and custom types

    """

    def __init__(  # ruff:ignore[too-many-arguments]  # public signature
        self,
        keys: Iterable[str],
        desc: str,
        of_type: type[T] | UnionType,
        default: Callable[[Config, str | None], T] | T | None,
        post_process: Callable[[T], T] | None = None,
        factory: Factory[T] | None = None,
    ) -> None:
        super().__init__(keys, desc)
        self.of_type = of_type
        self.default = default
        self.post_process = post_process
        self.factory = factory
        self._cache: T | _Missing = _Missing.MISSING

    @override
    def __call__(
        self,
        conf: Config,
        loaders: list[Loader[T]],
        args: ConfigLoadArgs,
    ) -> T:
        if self._cache is _Missing.MISSING:
            primary_key, *alias_keys = self.keys
            for loader in loaders:
                chain_key = f"{loader.section.key}.{primary_key}"
                try:
                    if chain_key in args.chain:
                        msg = f"circular chain detected {', '.join(args.chain[args.chain.index(chain_key) :])}"
                        raise CircularChainError(msg)
                finally:
                    args.chain.append(chain_key)
                try:
                    value = loader.load(primary_key, self.of_type, self.factory, conf, args, all_keys=alias_keys)
                except KeyError:
                    continue
                else:
                    break
                finally:
                    del args.chain[-1]
            else:
                if callable(self.default):
                    value = cast("Callable[[Config, str | None], T]", self.default)(conf, args.env_name)
                else:
                    # when the default is None the overloads guarantee T includes None
                    value = cast("T", self.default)
            if self.post_process is not None:
                value = self.post_process(value)
            self._cache = value
        return self._cache

    @override
    def __repr__(self) -> str:
        values = ((k, v) for k, v in self.__dict__.items() if k not in {"post_process", "_cache"} and v is not None)
        return f"{type(self).__name__}({', '.join(f'{k}={v}' for k, v in values)})"

    @override
    def __eq__(self, o: object) -> bool:
        if not isinstance(o, ConfigDynamicDefinition):
            return NotImplemented
        return super().__eq__(o) and (self.of_type, self.default, self.post_process) == (
            o.of_type,
            o.default,
            o.post_process,
        )

    @override
    def overwrite(self, value: T) -> None:
        self._cache = value


class _Missing(Enum):
    MISSING = auto()


__all__ = [
    "ConfigConstantDefinition",
    "ConfigDefinition",
    "ConfigDynamicDefinition",
    "ConfigLoadArgs",
]
