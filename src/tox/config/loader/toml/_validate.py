from __future__ import annotations

from inspect import isclass
from types import UnionType
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
)

from tox.config.types import Command

if TYPE_CHECKING:
    from ._api import TomlTypes


T = TypeVar("T")


def validate(val: TomlTypes, of_type: type[T]) -> T:  # noqa: C901, PLR0912
    casting_to = get_origin(of_type) or of_type.__class__
    type_args = get_args(of_type)
    msg = ""
    if casting_to in {list, list}:
        entry_type = type_args[0]
        if isinstance(val, list):
            for va in val:
                validate(va, entry_type)
        else:
            msg = f"{val!r} is not list"
    elif isclass(of_type) and issubclass(of_type, Command):
        # first we cast it to list then create commands, so for now validate it as a nested list
        validate(val, list[str])
    elif casting_to in {dict, dict}:
        key_type, value_type = type_args[0], type_args[1]
        if isinstance(val, dict):
            for va in val:
                validate(va, key_type)
            for va in val.values():
                validate(va, value_type)
        else:
            msg = f"{val!r} is not dictionary"
    elif casting_to in {Union, UnionType}:  # handle Optional values
        args: list[type[Any]] = list(type_args)
        for arg in args:
            try:
                validate(val, arg)
                break
            except TypeError:
                pass
        else:
            msg = f"{val!r} is not union of {', '.join(a.__name__ for a in args)}"
    elif casting_to in {Literal, type(Literal)}:
        choice = type_args
        if val not in choice:
            msg = f"{val!r} is not one of literal {','.join(repr(i) for i in choice)}"
    elif not isinstance(val, of_type):
        if issubclass(of_type, (bool, str, int)):
            fail = not isinstance(val, of_type)
        else:
            try:  # check if it can be converted
                of_type(val)
                fail = False
            except Exception:  # noqa: BLE001
                fail = True
        if fail:
            msg = f"{val!r} is not of type {of_type.__name__!r}"
    if msg:
        raise TypeError(msg)
    return cast("T", val)


__all__ = [
    "validate",
]
