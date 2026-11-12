from __future__ import annotations

from inspect import isclass
from types import UnionType
from typing import (
    TYPE_CHECKING,
    Literal,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
)

from tox.config.types import Command, EnvList

if TYPE_CHECKING:
    from collections.abc import Callable

    from ._api import TomlTypes


T = TypeVar("T")


def validate(val: TomlTypes, of_type: type[T]) -> T:
    """Check that a TOML value has the given type.

    :param val: the value to check
    :param of_type: the type the value must have

    :returns: the value, cast to the type

    :raises TypeError: when the value does not have the type

    """  # simplint: ignore[function-docstring]  # existing public docs
    casting_to = get_origin(of_type) or of_type.__class__
    type_args = get_args(of_type)
    msg = ""
    if casting_to in {list, list}:
        msg = _validate_list(val, type_args[0])
    elif isclass(of_type) and issubclass(of_type, Command):
        validate(val, list[str])
    elif isclass(of_type) and issubclass(of_type, EnvList):
        # validation is performed by TomlLoader.to_env_list
        pass
    elif casting_to in {dict, dict}:
        msg = _validate_dict(val, type_args[0], type_args[1])
    elif casting_to in {Union, UnionType}:
        msg = _validate_union(val, type_args)
    elif casting_to in {Literal, type(Literal)}:
        if val not in type_args:
            msg = f"{_describe(val)} is not one of literal {','.join(repr(i) for i in type_args)}"
    elif not isinstance(val, of_type):
        msg = _validate_instance(val, of_type)
    if msg:
        raise TypeError(msg)
    return cast("T", val)


def _validate_list(val: TomlTypes, entry_type: type) -> str:
    if not isinstance(val, list):
        return f"{_describe(val)} is not list"
    for va in val:
        validate(va, entry_type)
    return ""


def _validate_dict(val: TomlTypes, key_type: type, value_type: type) -> str:
    if not isinstance(val, dict):
        return f"{_describe(val)} is not dictionary"
    for key in val:
        validate(key, key_type)
    for item in val.values():
        validate(item, value_type)
    return ""


def _validate_union(val: TomlTypes, args: tuple[type, ...]) -> str:
    for arg in args:
        try:
            validate(val, arg)
        except TypeError:
            continue
        return ""
    return f"{_describe(val)} is not union of {', '.join(a.__name__ for a in args)}"


def _describe(value: TomlTypes) -> str:
    # Substitution can put secret text in values.
    if value is None or isinstance(value, (bool, int, float)):
        return repr(value)
    if isinstance(value, str):
        return "value of type 'str'"
    return f"value of type {type(value).__name__!r}"


def _validate_instance(val: TomlTypes, of_type: type[T]) -> str:
    if issubclass(of_type, (bool, str, int)):
        fail = True  # the enclosing branch established the value is not an instance already
    else:
        try:
            cast("Callable[[TomlTypes], object]", of_type)(val)
            fail = False
        except Exception:  # ruff:ignore[blind-except]  # failure must not stop run
            fail = True
    return f"{_describe(val)} is not of type {of_type.__name__!r}" if fail else ""


__all__ = [
    "validate",
]
