"""Convert string configuration values to tox python configuration objects."""

from __future__ import annotations

import shlex
import sys
from inspect import isclass
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from tox.config.loader.convert import Convert
from tox.config.types import Command, EnvList

if TYPE_CHECKING:
    from collections.abc import Iterator
    from io import StringIO
    from typing import Final


class StrConvert(Convert[str]):
    """A class converting string values to tox types."""

    @staticmethod
    def to_str(value: str) -> str:
        return str(value).strip()

    @staticmethod
    def to_path(value: str) -> Path:
        return Path(value)

    @staticmethod
    def to_list(value: str, of_type: type[Any]) -> Iterator[str]:
        splitter = "\n" if (isclass(of_type) and issubclass(of_type, Command)) or "\n" in value else ","
        splitter = splitter.replace("\r", "")
        for token in value.split(splitter):
            value = token.strip()
            if value:
                yield value

    @staticmethod
    def to_set(value: str, of_type: type[Any]) -> Iterator[str]:
        yield from StrConvert.to_list(value, of_type)

    @staticmethod
    def to_dict(value: str, of_type: tuple[type[Any], type[Any]]) -> Iterator[tuple[str, str]]:  # ruff:ignore[unused-static-method-argument]
        for row in value.split("\n"):
            if row.strip():
                key, sep, value = row.partition("=")
                if sep:
                    yield key.strip(), value.strip()
                else:
                    msg = f"dictionary lines must be of form key=value, found {row!r}"
                    raise TypeError(msg)

    @staticmethod
    def _win32_process_path_backslash(value: str, escape: str, special_chars: str) -> str:
        r"""Escape backslash in value that is not followed by a special character.

        This allows windows paths to be written without double backslash, while retaining the POSIX backslash escape
        semantics for quotes and escapes.

        A backslash pair at the very start of a word, immediately followed by more path text, is the exception: a UNC
        path (``\\server\share``) or an extended-length path prefix requires exactly two literal leading backslashes, so
        that leading pair must survive as-is rather than being collapsed the way an interior ``\\`` (the POSIX-escaped
        form of a single literal backslash) is elsewhere in a path. A bare ``\\`` with nothing (or only whitespace)
        after it is not a path prefix, and keeps the ordinary collapsing behavior.

        """
        result = []
        ix = 0
        at_word_start = True
        n = len(value)
        while ix < n:
            char = value[ix]
            if char.isspace():
                result.append(char)
                at_word_start = True
                ix += 1
                continue
            starts_backslash_pair = at_word_start and char == escape and value[ix + 1 : ix + 2] == escape
            if starts_backslash_pair:
                after_run = value[ix + 2 : ix + 3]
                if after_run and after_run != escape and not after_run.isspace():
                    # exactly two leading backslashes starting a word, followed by more text: a UNC/extended-path
                    # prefix - keep both backslashes literal instead of collapsing them
                    result.extend((escape * 2, escape * 2))
                    ix += 2
                    at_word_start = False
                    continue
            result.append(char)
            at_word_start = False
            if char == escape:
                last_char = value[ix - 1 : ix]
                if last_char != escape:
                    next_char = value[ix + 1 : ix + 2]
                    if next_char not in {escape, *special_chars}:
                        result.append(escape)  # escape escapes that are not themselves escaping a special character
            ix += 1
        return "".join(result)

    @staticmethod
    def to_command(value: str) -> Command:
        """At this point, ``value`` has already been substituted out, and all punctuation / escapes are final.

        Value will typically be stripped of whitespace when coming from an ini file.

        """
        value = value.replace(r"\#", "#")
        is_win = sys.platform == "win32"
        if is_win:  # pragma: win32 cover
            s = shlex.shlex(posix=True)
            value = StrConvert._win32_process_path_backslash(
                value,
                escape=s.escape,
                special_chars=s.quotes,
            )
        splitter = shlex.shlex(value, posix=True)
        splitter.whitespace_split = True
        splitter.commenters = ""  # comments handled earlier, and the shlex does not know escaped comment characters
        args: list[str] = []
        pos = 0
        try:
            for arg in splitter:
                if is_win and len(arg) > 1 and arg[0] == arg[-1] and arg.startswith(("'", '"')):  # pragma: win32 cover
                    # on Windows quoted arguments will remain quoted, strip it
                    arg = arg[1:-1]  # ruff:ignore[redefined-loop-name]
                args.append(arg)
                pos = cast("StringIO", splitter.instream).tell()
        except ValueError:
            args.append(value[pos:])
        if len(args) == 0:
            msg = f"attempting to parse {value!r} into a command failed"
            raise ValueError(msg)
        if args[0] != "-" and args[0].startswith("-"):
            args[0] = args[0][1:]
            args = ["-", *args]
        return Command(args)

    @staticmethod
    def to_env_list(value: str) -> EnvList:
        from tox.config.loader.ini.factor import extend_factors  # ruff:ignore[import-outside-top-level]

        elements = list(chain.from_iterable(extend_factors(expr) for expr in value.split("\n")))
        return EnvList(elements)

    TRUTHFUL_VALUES: Final[set[str]] = {"true", "1", "yes", "on"}
    FALSE_VALUES: Final[set[str]] = {"false", "0", "no", "off", ""}
    VALID_BOOL = sorted(TRUTHFUL_VALUES | FALSE_VALUES)

    @staticmethod
    def to_bool(value: str) -> bool:
        norm = str(value).strip().lower()
        if norm in StrConvert.TRUTHFUL_VALUES:
            return True
        if norm in StrConvert.FALSE_VALUES:
            return False

        msg = f"value {value!r} cannot be transformed to bool, valid: {', '.join(StrConvert.VALID_BOOL)}"
        raise TypeError(msg)


__all__ = ("StrConvert",)
