from __future__ import annotations

import typing
from abc import ABC, abstractmethod
from collections import OrderedDict
from inspect import isclass
from itertools import chain
from pathlib import Path
from typing import Any, Callable, Dict, Generic, Iterable, Iterator, List, Literal, Optional, Set, TypeVar, Union, cast

from tox.config.loader.ini.factor import find_factor_groups
from tox.config.types import Command, EnvList

_NO_MAPPING = object()
T = TypeVar("T")
V = TypeVar("V")

Factory = Optional[Callable[[object], T]]  # note the argument is anything, due e.g. memory loader can inject anything


class ConditionalValue(Generic[T]):
    """Value with a condition."""

    def __init__(self, value: T, condition: str | None) -> None:
        self.value = value
        self.condition = condition
        self._groups = tuple(find_factor_groups(condition)) if condition is not None else ()

    def matches(self, env_name: str) -> bool:
        """Return whether the value matches the environment name."""
        if self.condition is None:
            return True

        # Split env_name to factors.
        env_factors = set(chain.from_iterable([(i for i, _ in a) for a in find_factor_groups(env_name)]))

        matches = []
        for group in self._groups:
            group_matches = []
            for factor, negate in group:
                group_matches.append((factor in env_factors) ^ negate)
            matches.append(all(group_matches))
        return any(matches)


class ConditionalSetting(Generic[T]):
    """Setting whose value depends on various conditions."""

    def __init__(self, values: typing.Iterable[ConditionalValue[T]]) -> None:
        self.values = tuple(values)

    def filter(self, env_name: str) -> Iterable[T]:
        """Filter values for the environment."""
        for value in self.values:
            if value.matches(env_name):
                yield value.value


class Convert(ABC, Generic[T]):
    """A class that converts a raw type to a given tox (python) type."""

    def to(self, raw: T, of_type: type[V], factory: Factory[V]) -> V:  # noqa: PLR0911, C901
        """
        Convert given raw type to python type.

        :param raw: the raw type
        :param of_type: python type
        :param factory: factory method to build the object
        :return: the converted type
        """
        from_module = getattr(of_type, "__module__", None)
        if from_module in {"typing", "typing_extensions"}:
            return self._to_typing(raw, of_type, factory)
        if isclass(of_type):
            if issubclass(of_type, Path):
                return self.to_path(raw)  # type: ignore[return-value]
            if issubclass(of_type, bool):
                return self.to_bool(raw)  # type: ignore[return-value]
            if issubclass(of_type, Command):
                return self.to_command(raw)  # type: ignore[return-value]
            if issubclass(of_type, EnvList):
                return self.to_env_list(raw)  # type: ignore[return-value]
            if issubclass(of_type, str):
                return self.to_str(raw)  # type: ignore[return-value]
        # python does not allow use of parametrized generics with isinstance, so we need to check for them.
        if hasattr(typing, "GenericAlias") and isinstance(of_type, typing.GenericAlias):
            return list(self.to_list(raw, of_type=of_type))  # type: ignore[return-value]
        if isinstance(raw, of_type):  # already target type no need to transform it
            # do it this late to allow normalization - e.g. string strip
            return raw  # type: ignore[no-any-return]
        if factory:
            return factory(raw)
        return of_type(raw)  # type: ignore[no-any-return]

    def _to_typing(self, raw: T, of_type: type[V], factory: Factory[V]) -> V:  # noqa: C901
        origin = getattr(of_type, "__origin__", of_type.__class__)
        result: Any = _NO_MAPPING
        if origin in {list, List}:
            entry_type = of_type.__args__[0]  # type: ignore[attr-defined]
            result = [self.to(i, entry_type, factory) for i in self.to_list(raw, entry_type)]
        elif origin in {set, Set}:
            entry_type = of_type.__args__[0]  # type: ignore[attr-defined]
            result = {self.to(i, entry_type, factory) for i in self.to_set(raw, entry_type)}
        elif origin in {dict, Dict}:
            key_type, value_type = of_type.__args__[0], of_type.__args__[1]  # type: ignore[attr-defined]
            result = OrderedDict(
                (self.to(k, key_type, factory), self.to(v, value_type, factory))
                for k, v in self.to_dict(raw, (key_type, value_type))
            )
        elif origin == Union:  # handle Optional values
            args: list[type[Any]] = of_type.__args__  # type: ignore[attr-defined]
            none = type(None)
            if len(args) == 2 and none in args:  # noqa: PLR2004
                if isinstance(raw, str):
                    raw = raw.strip()  # type: ignore[assignment]
                if not raw:
                    result = None
                else:
                    new_type = next(i for i in args if i != none)  # pragma: no cover
                    result = self.to(raw, new_type, factory)
        elif origin in {Literal, type(Literal)}:
            choice = of_type.__args__  # type: ignore[attr-defined]
            if raw not in choice:
                msg = f"{raw} must be one of {choice}"
                raise ValueError(msg)
            result = raw
        if result is not _NO_MAPPING:
            return cast(V, result)
        msg = f"{raw} cannot cast to {of_type!r}"
        raise TypeError(msg)

    @staticmethod
    @abstractmethod
    def to_str(value: T) -> str:
        """
        Convert to string.

        :param value: the value to convert
        :returns: a string representation of the value
        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def to_bool(value: T) -> bool:
        """
        Convert to boolean.

        :param value: the value to convert
        :returns: a boolean representation of the value
        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def to_list(value: T, of_type: type[Any]) -> Iterator[T]:
        """
        Convert to list.

        :param value: the value to convert
        :param of_type: the type of elements in the list
        :returns: a list representation of the value
        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def to_set(value: T, of_type: type[Any]) -> Iterator[T]:
        """
        Convert to set.

        :param value: the value to convert
        :param of_type: the type of elements in the set
        :returns: a set representation of the value
        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def to_dict(value: T, of_type: tuple[type[Any], type[Any]]) -> Iterator[tuple[T, T]]:
        """
        Convert to dictionary.

        :param value: the value to convert
        :param of_type: a tuple indicating the type of the key and the value
        :returns: a iteration of key-value pairs that gets populated into a dict
        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def to_path(value: T) -> Path:
        """
        Convert to path.

        :param value: the value to convert
        :returns: path representation of the value
        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def to_command(value: T) -> Command:
        """
        Convert to a command to execute.

        :param value: the value to convert
        :returns: command representation of the value
        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def to_env_list(value: T) -> EnvList:
        """
        Convert to a tox EnvList.

        :param value: the value to convert
        :returns: a list of tox environments from the value
        """
        raise NotImplementedError


__all__ = [
    "Convert",
    "Factory",
]
