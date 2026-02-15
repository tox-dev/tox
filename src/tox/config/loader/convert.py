from __future__ import annotations

import typing
from abc import ABC, abstractmethod
from collections import OrderedDict
from collections.abc import Callable, Iterator
from inspect import isclass
from pathlib import Path
from types import UnionType
from typing import Any, Generic, Literal, TypeVar, Union, cast, get_args, get_origin

from tox.config.types import Command, EnvList

_NO_MAPPING = object()
T = TypeVar("T")
V = TypeVar("V")

Factory = Callable[[object], T] | None  # note the argument is anything, due e.g. memory loader can inject anything


class Convert(ABC, Generic[T]):
    """A class that converts a raw type to a given tox (python) type."""

    def to(self, raw: T, of_type: type[V] | UnionType, factory: Factory[V]) -> V:  # noqa: PLR0911
        """Convert given raw type to python type.

        :param raw: the raw type
        :param of_type: python type
        :param factory: factory method to build the object

        :returns: the converted type

        """
        from_module = getattr(of_type, "__module__", None)
        if (
            from_module in {"typing", "typing_extensions"}
            or of_type.__class__ == UnionType
            or (hasattr(typing, "GenericAlias") and isinstance(of_type, typing.GenericAlias))
        ):
            return self._to_typing(raw, of_type, factory)
        if isclass(of_type):
            if issubclass(of_type, Path):
                return cast("V", self.to_path(raw))
            if issubclass(of_type, bool):
                return cast("V", self.to_bool(raw))
            if issubclass(of_type, Command):
                return cast("V", self.to_command(raw))
            if issubclass(of_type, EnvList):
                return cast("V", self.to_env_list(raw))
            if issubclass(of_type, str):
                return cast("V", self.to_str(raw))
        if isinstance(raw, cast("type[V]", of_type)):  # already target type no need to transform it
            # do it this late to allow normalization - e.g. string strip
            return raw
        if factory:
            return factory(raw)
        return cast("type[V]", of_type)(raw)

    def _to_typing(self, raw: T, of_type: type[V] | UnionType, factory: Factory[V]) -> V:  # noqa: C901
        origin = get_origin(of_type) or of_type.__class__
        result: Any = _NO_MAPPING
        type_args = get_args(of_type)
        if origin in {list, list}:
            entry_type = type_args[0]
            result = [self.to(i, entry_type, factory) for i in self.to_list(raw, entry_type)]
            if isclass(entry_type) and issubclass(entry_type, Command):
                result = [i for i in result if i is not None]
        elif origin in {set, set}:
            entry_type = type_args[0]
            result = {self.to(i, entry_type, factory) for i in self.to_set(raw, entry_type)}
        elif origin in {dict, dict}:
            key_type, value_type = type_args[0], type_args[1]
            result = OrderedDict(
                (self.to(k, key_type, factory), self.to(v, value_type, factory))
                for k, v in self.to_dict(raw, (key_type, value_type))
            )
        elif origin in {Union, UnionType}:  # handle Optional values
            args: list[type[Any]] = list(type_args)
            none = type(None)
            if len(args) == 2 and none in args:  # noqa: PLR2004
                if isinstance(raw, str):
                    raw = cast("T", raw.strip())
                if raw is None or (isinstance(raw, str) and not raw):
                    result = None
                else:
                    new_type = next(i for i in args if i != none)  # pragma: no cover
                    result = self.to(raw, new_type, factory)
        elif origin in {Literal, type(Literal)}:
            choice = type_args
            if raw not in choice:
                msg = f"{raw} must be one of {choice}"
                raise ValueError(msg)
            result = raw
        if result is not _NO_MAPPING:
            return cast("V", result)
        msg = f"{raw} cannot cast to {of_type!r}"
        raise TypeError(msg)

    @staticmethod
    @abstractmethod
    def to_str(value: T) -> str:
        """Convert to string.

        :param value: the value to convert

        :returns: a string representation of the value

        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def to_bool(value: T) -> bool:
        """Convert to boolean.

        :param value: the value to convert

        :returns: a boolean representation of the value

        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def to_list(value: T, of_type: type[Any]) -> Iterator[T]:
        """Convert to list.

        :param value: the value to convert
        :param of_type: the type of elements in the list

        :returns: a list representation of the value

        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def to_set(value: T, of_type: type[Any]) -> Iterator[T]:
        """Convert to set.

        :param value: the value to convert
        :param of_type: the type of elements in the set

        :returns: a set representation of the value

        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def to_dict(value: T, of_type: tuple[type[Any], type[Any]]) -> Iterator[tuple[T, T]]:
        """Convert to dictionary.

        :param value: the value to convert
        :param of_type: a tuple indicating the type of the key and the value

        :returns: a iteration of key-value pairs that gets populated into a dict

        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def to_path(value: T) -> Path:
        """Convert to path.

        :param value: the value to convert

        :returns: path representation of the value

        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def to_command(value: T) -> Command | None:
        """Convert to a command to execute.

        :param value: the value to convert

        :returns: command representation of the value

        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def to_env_list(value: T) -> EnvList:
        """Convert to a tox EnvList.

        :param value: the value to convert

        :returns: a list of tox environments from the value

        """
        raise NotImplementedError


__all__ = [
    "Convert",
    "Factory",
]
