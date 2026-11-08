"""Convert string configuration values to tox python configuration objects."""

from __future__ import annotations

import shlex
import sys
from inspect import isclass
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from tox.config.types import Command, EnvList
from tox.util.typing_compat import override

from .convert import Convert

if TYPE_CHECKING:
    from collections.abc import Iterator
    from io import StringIO
    from typing import Final


class StrConvert(Convert[str]):
    """A class converting string values to tox types.

    :var TRUTHFUL_VALUES: the strings that convert to ``True``
    :var FALSE_VALUES: the strings that convert to ``False``
    :var VALID_BOOL: the sorted list of all accepted boolean strings

    """

    @staticmethod
    @override
    def to_str(value: str) -> str:
        return str(value).strip()

    @staticmethod
    @override
    def to_path(value: str) -> Path:
        if not value.strip():
            msg = "path value is empty (does it reference an unset variable?)"
            raise ValueError(msg)
        return Path(value)

    @staticmethod
    @override
    def to_set(  # simplint: ignore[SMP602]  # converts strings into any configured type
        value: str,
        of_type: type[Any],  # simplint: ignore[SMP602]  # converts strings into any configured type
    ) -> Iterator[str]:
        yield from StrConvert.to_list(value, of_type)

    @staticmethod
    @override
    def to_list(  # simplint: ignore[SMP602]  # converts strings into any configured type
        value: str,
        of_type: type[Any],  # simplint: ignore[SMP602]  # converts strings into any configured type
    ) -> Iterator[str]:
        splitter = "\n" if (isclass(of_type) and issubclass(of_type, Command)) or "\n" in value else ","
        splitter = splitter.replace("\r", "")
        for token in value.split(splitter):
            value = token.strip()
            if value:
                yield value

    @staticmethod
    @override
    def to_dict(  # simplint: ignore[SMP602]  # converts strings into any configured type
        value: str,
        of_type: tuple[type[Any], type[Any]],  # simplint: ignore[SMP602]  # converts strings into any configured type
    ) -> Iterator[tuple[str, str]]:
        for row in value.split("\n"):
            if row.strip():
                key, sep, value = row.partition("=")
                if sep:
                    yield key.strip(), value.strip()
                else:
                    msg = f"dictionary lines must be of form key=value, found {row!r}"
                    raise TypeError(msg)

    @staticmethod
    @override
    def to_command(value: str) -> Command:
        """At this point, ``value`` has already been substituted out, and all punctuation / escapes are final.

        Value will typically be stripped of whitespace when coming from an ini file.

        """
        if sys.platform == "win32":  # pragma: win32 cover
            value = StrConvert.protect_windows_path_backslashes(value)
        splitter = shlex.shlex(value, posix=True)
        splitter.whitespace_split = True
        splitter.commenters = ""  # comments handled earlier, and the shlex does not know escaped comment characters
        args: list[str] = []
        pos = 0
        try:
            for arg in splitter:
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
    def protect_windows_path_backslashes(value: str) -> str:
        """Allow Windows paths while retaining shlex quote and backslash escapes.

        :param value: the value to protect

        :returns: the value with the Windows path backslashes kept

        """
        defaults: Final[shlex.shlex] = shlex.shlex(posix=True)
        escape: Final[str] = defaults.escape
        special_chars: Final[str] = defaults.quotes
        result: Final[list[str]] = []
        quote = ""
        path_start = True
        index = 0
        while index < len(value):
            char = value[index]
            if quote == "'":
                result.append(char)
                if char == quote:
                    quote = ""
                path_start = False
            elif char == escape:
                text, consumed = _escape_text(value, index, escape, special_chars, path_start=path_start)
                result.append(text)
                index += consumed
                path_start = False
                continue
            else:
                result.append(char)
                if char in special_chars and not quote:
                    quote = char
                    path_start = True
                elif char == quote:
                    quote = ""
                    path_start = False
                else:
                    path_start = (not quote and char in " \t\r\n") or char == "="
            index += 1
        return "".join(result)

    @staticmethod
    @override
    def to_env_list(value: str) -> EnvList:
        from .ini.factor import extend_factors  # ruff:ignore[import-outside-top-level]  # avoids an import cycle

        return EnvList(list(chain.from_iterable(extend_factors(expr) for expr in value.split("\n"))))

    TRUTHFUL_VALUES: Final[set[str]] = {"true", "1", "yes", "on"}
    FALSE_VALUES: Final[set[str]] = {"false", "0", "no", "off", ""}
    VALID_BOOL = sorted(TRUTHFUL_VALUES | FALSE_VALUES)

    @staticmethod
    @override
    def to_bool(value: str) -> bool:
        norm = str(value).strip().lower()
        if norm in StrConvert.TRUTHFUL_VALUES:
            return True
        if norm in StrConvert.FALSE_VALUES:
            return False

        msg = f"value {value!r} cannot be transformed to bool, valid: {', '.join(StrConvert.VALID_BOOL)}"
        raise TypeError(msg)


def _escape_text(value: str, index: int, escape: str, special_chars: str, *, path_start: bool) -> tuple[str, int]:
    if (following := value[index + 1 : index + 2]) == escape:
        after_pair = value[index + 2 : index + 3]
        # UNC prefixes need two literal backslashes; a bare pair still escapes one.
        is_prefix = path_start and bool(after_pair) and after_pair not in f"{escape}{special_chars} \t\r\n"
        return escape * (4 if is_prefix else 2), 2
    if following and following in special_chars:
        return escape + following, 2
    return (escape if value[index - 1 : index] == escape else escape * 2), 1


__all__ = [
    "StrConvert",
]
