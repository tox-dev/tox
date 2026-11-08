from __future__ import annotations

import typing
from abc import ABC, abstractmethod
from collections import OrderedDict
from collections.abc import Callable, Iterator
from enum import Enum, auto
from inspect import isclass
from pathlib import Path
from types import UnionType
from typing import Any, Generic, Literal, TypeVar, Union, cast, get_args, get_origin

from tox.config.types import Command, EnvList


class _Missing(Enum):
    MISSING = auto()


RawT = TypeVar("RawT")
ValueT = TypeVar("ValueT")

Factory = Callable[[object], RawT] | None  # note the argument is anything, due e.g. memory loader can inject anything
"""Callable that converts a raw value to the target type, or ``None`` when no conversion is needed."""


class Convert(ABC, Generic[RawT]):
    """A class that converts a raw type to a given tox (python) type."""

    def to(  # ruff:ignore[too-many-return-statements]  # distinct outcomes
        self, raw: RawT, of_type: type[ValueT] | UnionType, factory: Factory[ValueT]
    ) -> ValueT:
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
                return cast("ValueT", self.to_path(raw))
            if issubclass(of_type, bool):
                return cast("ValueT", self.to_bool(raw))
            if issubclass(of_type, Command):
                return cast("ValueT", self.to_command(raw))
            if issubclass(of_type, EnvList):
                return cast("ValueT", self.to_env_list(raw))
            if issubclass(of_type, str):
                return cast("ValueT", self.to_str(raw))
        if isinstance(raw, cast("type[ValueT]", of_type)):  # already target type no need to transform it
            # do it this late to allow normalization - e.g. string strip
            return raw
        if factory:
            return factory(raw)
        return cast("Callable[[RawT], ValueT]", of_type)(raw)

    def _to_typing(  # ruff:ignore[complex-structure, too-many-branches]  # follows the protocol
        self, raw: RawT, of_type: type[ValueT] | UnionType, factory: Factory[ValueT]
    ) -> ValueT:
        origin = get_origin(of_type) or of_type.__class__
        result: Any = _Missing.MISSING
        type_args = get_args(of_type)
        if origin in {list, list}:
            entry_type = type_args[0]
            result = [self.to(i, entry_type, factory) for i in self.to_list(raw, entry_type)]
        elif origin in {set, set}:
            entry_type = type_args[0]
            result = {self.to(i, entry_type, factory) for i in self.to_set(raw, entry_type)}
        elif origin in {dict, dict}:
            key_type, value_type = type_args[0], type_args[1]
            result = OrderedDict(
                (self.to(k, key_type, factory), self.to(v, value_type, factory))
                for k, v in self.to_dict(raw, (key_type, value_type))
            )
        elif origin in {Union, UnionType}:
            args: list[type | UnionType] = list(type_args)
            none = type(None)
            if len(args) == 2 and none in args:  # ruff:ignore[magic-value-comparison]  # fixed protocol value
                if isinstance(raw, str):
                    raw = cast("RawT", raw.strip())
                if raw is None or (isinstance(raw, str) and not raw):
                    result = None
                else:
                    new_type = next(i for i in args if i != none)  # pragma: no cover  # setup not built by tests
                    result = self.to(raw, new_type, factory)
            elif any(get_origin(arg) is not None for arg in args):
                for arg in args:
                    try:
                        result = self.to(raw, arg, factory)
                        break
                    except (TypeError, ValueError):
                        pass
        elif origin in {Literal, type(Literal)}:
            choice = type_args
            if raw not in choice:
                msg = f"{raw} must be one of {choice}"
                raise ValueError(msg)
            result = raw
        if result is not _Missing.MISSING:
            return cast("ValueT", result)
        msg = f"{raw} cannot cast to {of_type!r}"
        raise TypeError(msg)

    @staticmethod
    @abstractmethod
    def to_list(value: RawT, of_type: type) -> Iterator[RawT]:
        """Convert to list.

        :param value: the value to convert
        :param of_type: the type of elements in the list

        :returns: a list representation of the value

        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def to_set(value: RawT, of_type: type) -> Iterator[RawT]:
        """Convert to set.

        :param value: the value to convert
        :param of_type: the type of elements in the set

        :returns: a set representation of the value

        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def to_dict(value: RawT, of_type: tuple[type, type]) -> Iterator[tuple[RawT, RawT]]:
        """Convert to dictionary.

        :param value: the value to convert
        :param of_type: a tuple indicating the type of the key and the value

        :returns: a iteration of key-value pairs that gets populated into a dict

        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def to_path(value: RawT) -> Path:
        """Convert to path.

        :param value: the value to convert

        :returns: path representation of the value

        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def to_bool(value: RawT) -> bool:
        """Convert to boolean.

        :param value: the value to convert

        :returns: a boolean representation of the value

        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def to_command(value: RawT) -> Command:
        """Convert to a command to execute.

        :param value: the value to convert

        :returns: command representation of the value

        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def to_env_list(value: RawT) -> EnvList:
        """Convert to a tox EnvList.

        :param value: the value to convert

        :returns: a list of tox environments from the value

        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def to_str(value: RawT) -> str:
        """Convert to string.

        :param value: the value to convert

        :returns: a string representation of the value

        """
        raise NotImplementedError


__all__ = [
    "Convert",
    "Factory",
]
