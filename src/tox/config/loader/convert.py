import sys
from abc import ABC, abstractmethod
from collections import OrderedDict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Generic, Iterator, List, Set, Tuple, Type, TypeVar, Union, cast

from ..types import Command, EnvList

if sys.version_info >= (3, 8):  # pragma: no cover (py38+)
    from typing import Literal
else:  # pragma: no cover (py38+)
    from typing_extensions import Literal  # noqa


_NO_MAPPING = object()
T = TypeVar("T")
V = TypeVar("V")


class Convert(ABC, Generic[T]):
    """A class that converts a raw type to a given tox (python) type"""

    def to(self, raw: T, of_type: Type[V]) -> V:
        from_module = getattr(of_type, "__module__", None)
        if from_module in ("typing", "typing_extensions"):
            return self._to_typing(raw, of_type)  # type: ignore[return-value]
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
        elif isinstance(raw, of_type):
            return raw
        elif issubclass(of_type, Enum):
            return cast(V, getattr(of_type, str(raw)))
        return of_type(raw)  # type: ignore[call-arg]

    def _to_typing(self, raw: T, of_type: Type[V]) -> V:
        origin = getattr(of_type, "__origin__", of_type.__class__)
        result: Any = _NO_MAPPING
        if origin in (list, List):
            entry_type = of_type.__args__[0]  # type: ignore[attr-defined]
            result = [self.to(i, entry_type) for i in self.to_list(raw, entry_type)]
        elif origin in (set, Set):
            entry_type = of_type.__args__[0]  # type: ignore[attr-defined]
            result = {self.to(i, entry_type) for i in self.to_set(raw, entry_type)}
        elif origin in (dict, Dict):
            key_type, value_type = of_type.__args__[0], of_type.__args__[1]  # type: ignore[attr-defined]
            result = OrderedDict(
                (self.to(k, key_type), self.to(v, value_type)) for k, v in self.to_dict(raw, (key_type, value_type))
            )
        elif origin == Union:  # handle Optional values
            args: List[Type[Any]] = of_type.__args__  # type: ignore[attr-defined]
            none = type(None)
            if len(args) == 2 and none in args:
                if isinstance(raw, str):
                    raw = raw.strip()  # type: ignore[assignment]
                if not raw:
                    result = None
                else:
                    new_type = next(i for i in args if i != none)  # pragma: no cover # this will always find a element
                    result = self.to(raw, new_type)
        elif origin == Literal or origin == type(Literal):
            if sys.version_info >= (3, 7):  # pragma: no cover (py37+)
                choice = of_type.__args__
            else:  # pragma: no cover (py38+)
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
    def to_list(value: T, of_type: Type[Any]) -> Iterator[T]:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def to_set(value: T, of_type: Type[Any]) -> Iterator[T]:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def to_dict(value: T, of_type: Tuple[Type[Any], Type[Any]]) -> Iterator[Tuple[T, T]]:
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
