"""The ``KEY=VALUE; marker`` line syntax of ``set_env`` text in INI files and ``--override`` values."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, NamedTuple

from .loader.replacer import HostText

if TYPE_CHECKING:
    from typing import Final


def split_line(line: str) -> _SplitLine:
    """Split a ``KEY=VALUE`` line into its key, its value and its marker.

    :param line: the line to split

    :returns: the key, the value and the marker, the marker being empty when the line has none

    :raises ValueError: when the line has no ``=``

    """
    key, sep, rest = line.partition("=")
    if not sep:
        msg = f"invalid line {line!r} in set_env"
        raise ValueError(msg)
    if isinstance(line, HostText):
        rest = line.fragment(len(key) + 1)
    value, marker = split_value_marker(rest.strip())
    return _SplitLine(key.strip(), value, marker)


def split_value_marker(value: str) -> tuple[str, str]:
    # Quotes keep a ";" inside a quoted value from being read as the marker separator, but only when balanced -- a lone
    # quote (e.g. an apostrophe in the value) must not swallow the marker, so retry ignoring quotes if one is left open.
    """Split a value from the marker that follows a ``;`` outside of quotes.

    :param value: the value, possibly followed by a marker

    :returns: the value and the marker, the marker being empty when there is none

    """
    respect_quotes = True
    while True:  # the second pass ignores quotes, so it always ends balanced
        marker_at, in_quotes = _marker_position(value, respect_quotes=respect_quotes)
        if marker_at is not None:
            text: str = value.fragment(0, marker_at) if isinstance(value, HostText) else value[:marker_at]
            return _unescape_semicolons(text.strip()), value[marker_at + 1 :].strip()
        if not in_quotes:
            return _unescape_semicolons(value), ""
        respect_quotes = False


def _marker_position(value: str, *, respect_quotes: bool) -> tuple[int | None, bool]:
    in_quotes = False
    quote_char = ""
    for index, char in enumerate(value):
        if respect_quotes and char in {'"', "'"} and not _quote_is_escaped(value, index):
            if not in_quotes:
                in_quotes, quote_char = True, char
            elif char == quote_char:
                in_quotes = False
        # one backslash is enough: C:\tools\\;C:\bin means C:\tools\ followed by an escaped semicolon
        elif char == ";" and not in_quotes and (index == 0 or value[index - 1] != "\\"):
            return index, in_quotes
    return None, in_quotes


def _quote_is_escaped(value: str, index: int) -> bool:
    # an even run of backslashes is literal, so the closing quote of "C:\bin\\" still closes
    before = value[:index]
    return (len(before) - len(before.rstrip("\\"))) % 2 == 1


def _unescape_semicolons(value: str) -> str:
    if "\\;" not in value:
        return value
    if not isinstance(value, HostText):
        return value.replace("\\;", ";")
    parts: Final[list[str]] = []
    offset = 0
    for match in _MATCH_PATTERN.finditer(value):
        parts.extend((value.fragment(offset, match.start()), value.fragment(match.start() + 1, match.end())))
        offset = match.end()
    parts.append(value.fragment(offset))
    return HostText.from_parts(parts)


class _SplitLine(NamedTuple):
    key: str
    value: str
    marker: str


_MATCH_PATTERN: Final[re.Pattern[str]] = re.compile(r"\\;")


def format_line(key: str, value: str, marker: str | None) -> str:
    """Format a ``KEY=VALUE`` line, the inverse of splitting it.

    :param key: the environment variable name
    :param value: the value, with ``;`` escaped
    :param marker: the marker to append, ``None`` for none

    :returns: the formatted line

    """
    escaped_semicolon: Final[str] = r"\;"  # Python 3.11 rejects a backslash inside an f-string expression
    line = f"{key}={value.replace(';', escaped_semicolon)}"
    return f"{line}; {marker}" if marker else line


__all__ = [
    "format_line",
    "split_line",
    "split_value_marker",
]
