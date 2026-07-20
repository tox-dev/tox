"""Group together configuration values (such as base tox configuration, tox environment configs)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar, cast

from tox.config.loader.api import ConfigLoadArgs, Loader
from tox.config.types import CircularChainError

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from types import UnionType

    from tox.config.loader.convert import Factory
    from tox.config.main import Config  # pragma: no cover


T = TypeVar("T")
V = TypeVar("V")


class ConfigDefinition(ABC, Generic[T]):  # ruff:ignore[eq-without-hash]
    """Abstract base class for configuration definitions."""

    def __init__(self, keys: Iterable[str], desc: str) -> None:
        self.keys = keys
        self.desc = desc

    @abstractmethod
    def __call__(self, conf: Config, loaders: list[Loader[T]], args: ConfigLoadArgs) -> T:
        raise NotImplementedError

    @abstractmethod
    def overwrite(self, value: T) -> None:
        """Force the configuration to the given value, replacing any constant or already loaded one."""
        raise NotImplementedError

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, ConfigDefinition):
            return False
        return (self.keys, self.desc) == (o.keys, o.desc)

    def __ne__(self, o: object) -> bool:
        return not (self == o)


class ConfigConstantDefinition(ConfigDefinition[T]):  # ruff:ignore[eq-without-hash]
    """A configuration definition whose value is defined upfront (such as the tox environment name)."""

    def __init__(
        self,
        keys: Iterable[str],
        desc: str,
        value: Callable[[], T] | T,
    ) -> None:
        super().__init__(keys, desc)
        self.value = value

    def __call__(
        self,
        conf: Config,  # ruff:ignore[unused-method-argument]
        loaders: list[Loader[T]],  # ruff:ignore[unused-method-argument]
        args: ConfigLoadArgs,  # ruff:ignore[unused-method-argument]
    ) -> T:
        if callable(self.value):
            return cast("Callable[[], T]", self.value)()
        return self.value

    def overwrite(self, value: T) -> None:
        self.value = value

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, ConfigConstantDefinition):
            return False
        return super().__eq__(o) and self.value == o.value

    def __repr__(self) -> str:
        values = ((k, v) for k, v in vars(self).items() if v is not None)
        return f"{type(self).__name__}({', '.join(f'{k}={v}' for k, v in values)})"


_PLACE_HOLDER = object()


class ConfigDynamicDefinition(ConfigDefinition[T]):  # ruff:ignore[eq-without-hash]
    """A configuration definition that comes from a source (such as in memory, an ini file, a toml file, etc.)."""

    def __init__(  # ruff:ignore[too-many-arguments]
        self,
        keys: Iterable[str],
        desc: str,
        of_type: type[T] | UnionType,
        default: Callable[[Config, str | None], T] | T,
        post_process: Callable[[T], T] | None = None,
        factory: Factory[T] | None = None,
    ) -> None:
        super().__init__(keys, desc)
        self.of_type = of_type
        self.default = default
        self.post_process = post_process
        self.factory = factory
        self._cache: object | T = _PLACE_HOLDER

    def __call__(
        self,
        conf: Config,
        loaders: list[Loader[T]],
        args: ConfigLoadArgs,
    ) -> T:
        if self._cache is _PLACE_HOLDER:
            primary_key, *alias_keys = self.keys
            for loader in loaders:
                chain_key = f"{loader.section.key}.{primary_key}"
                try:
                    if chain_key in args.chain:
                        values = args.chain[args.chain.index(chain_key) :]
                        msg = f"circular chain detected {', '.join(values)}"
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
                    value = self.default
            if self.post_process is not None:
                value = self.post_process(value)
            self._cache = value
        return cast("T", self._cache)

    def overwrite(self, value: T) -> None:
        self._cache = value

    def __repr__(self) -> str:
        values = ((k, v) for k, v in vars(self).items() if k not in {"post_process", "_cache"} and v is not None)
        return f"{type(self).__name__}({', '.join(f'{k}={v}' for k, v in values)})"

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, ConfigDynamicDefinition):
            return False
        return super().__eq__(o) and (self.of_type, self.default, self.post_process) == (
            o.of_type,
            o.default,
            o.post_process,
        )


__all__ = [
    "ConfigConstantDefinition",
    "ConfigDefinition",
    "ConfigDynamicDefinition",
    "ConfigLoadArgs",
]
