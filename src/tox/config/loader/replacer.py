"""Apply value substitution (replacement) on tox strings."""

from __future__ import annotations

import dataclasses
import glob
import logging
import os
import re
import shlex
import sys
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Iterator, Sequence
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Protocol, TypeVar, Union, get_args, get_origin

from tox.config.types import CircularChainError, Command, EnvList
from tox.util.typing_compat import override

if TYPE_CHECKING:
    from types import UnionType
    from typing import Self

    from tox.config.main import Config
    from tox.config.set_env import SetEnv

    from .api import ConfigLoadArgs


LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# split alongside :, unless it is preceded by a single capital letter (Windows drive letters in paths)
ARG_DELIMITER: Final[str] = ":"
REPLACE_START: Final[str] = "{"
REPLACE_END: Final[str] = "}"
BACKSLASH_ESCAPE_CHARS: Final[tuple[str, ...]] = (ARG_DELIMITER, REPLACE_START, REPLACE_END, "[", "]")
MAX_REPLACE_DEPTH: Final[int] = 100
"""Maximum depth of nested replacements, deeper ones are not expanded."""
# Factor overrides can supply values absent from the configuration without renaming environments.
_FACTOR_ENV_PREFIX: Final[str] = "TOX_FACTOR_"
_REQUIREMENT_LINE_BREAKS: Final[str] = r"[\n\r\v\f\x1c-\x1e\x85\u2028\u2029]"


class MatchRecursionError(ValueError):
    """Could not stabilize on replacement value."""

    @staticmethod
    def check(depth: int, value: Any) -> None:
        """Raise an error when the replacement depth is beyond the maximum.

        :param depth: the current replacement depth
        :param value: the value being replaced

        :raises MatchRecursionError: when the depth is beyond the maximum
        """
        if depth > MAX_REPLACE_DEPTH:
            msg = f"Could not expand {value} after recursing {depth} frames"
            raise MatchRecursionError(msg)


class MatchError(Exception):
    """Couldn't find end terminator in MatchExpression."""


class RawText(str):  # ruff:ignore[subclass-builtin] # keep the origin through the str replacement interface
    """Text that is not subject to replacement, as it came from the configuration itself."""

    __slots__ = ()


class ReplaceReference(ABC):
    """A reference to a replacement, which knows how to resolve the names it is given."""

    @abstractmethod
    def __call__(self, value: str, conf_args: ConfigLoadArgs) -> str | ConfigDefault | None:
        """Perform a reference replacement.

        :param value: the raw value
        :param conf_args: the configuration loads argument object

        :returns: replacement text, an authored fallback, or None if no reference matches

        """
        raise NotImplementedError


MatchArg = Sequence[Union[str, "MatchExpression"]]
"""The arguments of a replacement, as plain text or as nested replacement expressions."""
_OtherFragment = TypeVar("_OtherFragment")


def find_replace_expr(value: str | MatchExpression) -> MatchArg:
    """Find all replaceable tokens within value.

    :param value: the text or expression to scan for replaceable tokens

    :returns: the replaceable tokens found, in order

    """
    if isinstance(value, MatchExpression):
        return [value]
    return MatchExpression.parse_and_split_to_terminator(value)[0][0]


def replace_command_lines(
    conf: Config, reference: ReplaceReference, value: str | MatchExpression, args: ConfigLoadArgs
) -> str:
    """Replace all active tokens within value, where each line of value is one command.

    :param conf: the configuration to resolve the tokens against
    :param reference: the configuration key the value belongs to
    :param value: the command lines to expand
    :param args: the loader arguments that scope the lookup

    :returns: the value with every active token replaced

    """
    replacer: Final[CommandLinesReplacer] = CommandLinesReplacer(conf, reference, conf_args=args)
    replacer.program = True
    return replacer.expand(value)


def replace_program(conf: Config, reference: ReplaceReference, value: str, args: ConfigLoadArgs) -> str:
    """Replace the tokens of a value that names a program to run.

    :param conf: the global config
    :param reference: the reference the value comes from
    :param value: the value to replace
    :param args: env args

    :returns: the value with its replacements resolved
    """
    replacer: Final[Replacer] = Replacer(conf, reference, conf_args=args)
    replacer.program = True
    return replacer.expand(value)


def replace_requirement_lines(
    conf: Config,
    reference: ReplaceReference,
    value: str | MatchExpression,
    args: ConfigLoadArgs,
    *,
    callbacks: RequirementLineCallbacks,
) -> str:
    """Replace the tokens of a requirements value, line by line.

    :param conf: the global config
    :param reference: the reference the value comes from
    :param value: the value to replace
    :param args: env args
    :param callbacks: the validation and protection callbacks for requirement lines

    :returns: the value with its replacements resolved
    """
    return RequirementLinesReplacer(conf, reference, conf_args=args, callbacks=callbacks).expand(value)


def replace_for(
    of_type: type[object] | UnionType,
) -> Callable[[Config, ReplaceReference, str | MatchExpression, ConfigLoadArgs], str]:
    """Get the replacement function for a value type.

    :param of_type: the type of the value to replace

    :returns: the function that replaces the tokens of a value of that type
    """
    kinds: Final[set[type | UnionType]] = {get_origin(kind) or kind for kind in (of_type, *get_args(of_type))}
    if of_type == list[Command]:
        return replace
    if EnvList in kinds:
        return partial(replace_entries, separators=",\n{}")
    if dict in kinds:
        return partial(replace_entries, separators="\n")
    if kinds & {list, set}:
        return replace_entries
    return replace


def replace(
    conf: Config, reference: ReplaceReference, value: str | MatchExpression, args: ConfigLoadArgs, depth: int = 0
) -> str:
    """Replace all active tokens within value according to the config.

    :param conf: the configuration to resolve the tokens against
    :param reference: the configuration key the value belongs to
    :param value: the text or expression to expand
    :param args: the loader arguments that scope the lookup
    :param depth: the current nesting depth, which stops runaway recursive references

    :returns: the value with every active token replaced

    """
    return Replacer(conf, reference, conf_args=args, depth=depth).expand(value)


def replace_entries(
    conf: Config,
    reference: ReplaceReference,
    value: str | MatchExpression,
    args: ConfigLoadArgs,
    *,
    separators: str = ",\n",
) -> str:
    """Replace the tokens of a value that holds a list of entries.

    :param conf: the global config
    :param reference: the reference the value comes from
    :param value: the value to replace
    :param args: env args
    :param separators: the characters that separate the entries

    :returns: the value with its replacements resolved
    """
    return EntriesReplacer(conf, reference, conf_args=args, separators=separators).expand(value)


def replace_once(conf: Config, reference: ReplaceReference, value: str | MatchExpression, args: ConfigLoadArgs) -> str:
    """Replace the active tokens within value, but not the tokens within the text they are replaced with.

    :param conf: the configuration to resolve the tokens against
    :param reference: the configuration key the value belongs to
    :param value: the text or expression whose tokens are replaced once
    :param args: the loader arguments that scope the lookup

    :returns: the value with its active tokens replaced, without expanding the replacements

    """
    return Replacer(conf, reference, conf_args=args, recursive=False).join(find_replace_expr(value))


class MatchExpression:  # ruff:ignore[eq-without-hash]  # mutable value type
    """An expression that is handled specially by the Replacer.

    :param expr: the parsed parts of the expression
    :param term_pos: the position in the source text where the expression ends
    :param host: whether the expression comes from a host variable
    :param literal: whether the expression is kept as written

    """

    def __init__(
        self, expr: Sequence[MatchArg], term_pos: int | None = None, *, host: bool = False, literal: bool = False
    ) -> None:
        self.expr = expr
        self.term_pos = term_pos
        self.host = host
        self.literal = literal

    @override
    def __repr__(self) -> str:
        return f"MatchExpression(expr={self.expr!r}, term_pos={self.term_pos!r})"

    @override
    def __eq__(self, other: object) -> bool:
        if isinstance(other, type(self)):
            return self.expr == other.expr
        return NotImplemented

    @classmethod
    def _next_replace_expression(cls, value: str) -> MatchExpression | None:
        # Process a curly brace replacement expression.
        if value.startswith("[]"):
            # `[]` is shorthand for `{posargs}`
            return MatchExpression(expr=[["posargs"]], term_pos=1)
        if not value.startswith(REPLACE_START):
            return None
        try:
            # recursively handle inner expression
            rec_expr, term_pos = cls.parse_and_split_to_terminator(
                cls._fragment(value, 1),
                terminator=REPLACE_END,
                split=ARG_DELIMITER,
            )
        except MatchError:
            # didn't find the expected terminator character, so treat `{` as if escaped.
            pass
        else:
            return MatchExpression(
                expr=rec_expr,
                term_pos=term_pos,
                host=isinstance(value, HostText) and value.covers(term_pos + 1),
                literal=isinstance(value, HostText) and value.covers_literal(term_pos + 1),
            )
        return None

    @classmethod
    def parse_and_split_to_terminator(
        cls,
        value: str,
        terminator: str = "",
        split: str | None = None,
    ) -> tuple[Sequence[MatchArg], int]:
        """Tokenize `value` to up `terminator` character.

        If `split` is given, multiple arguments will be returned.

        Returns list of arguments (list of str or MatchExpression) and final character position examined in value.

        This function recursively calls itself via `_next_replace_expression`.

        :param value: the text to tokenize
        :param terminator: the character that ends the tokenized text
        :param split: the character that separates multiple arguments

        :returns: the parsed arguments and the position where tokenizing stopped

        :raises MatchError: when the text does not form a valid expression

        """
        args = []
        last_arg: list[str | MatchExpression] = []
        pos = 0

        while pos < len(value):
            if (escaped := cls._escaped_fragment(value, pos)) is not None:
                last_arg.append(escaped)
                pos += 2
                continue
            if terminator and value.startswith(terminator, pos):
                pos += len(terminator)
                break
            if split and value.startswith(split, pos):
                # found a new argument
                args.append(last_arg)
                last_arg = []
                pos += len(split)
                continue
            if (value[pos] == REPLACE_START or value.startswith("[]", pos)) and (
                expr := cls._next_replace_expression(cls._fragment(value, pos))
            ) is not None:
                pos += (expr.term_pos or 0) + 1
                last_arg.append(expr)
                continue
            next_pos = cls._next_special_position(value, pos, terminator, split)
            last_arg.append(cls._fragment(value, pos, next_pos))
            pos = next_pos
        else:  # fell out of the loop
            if terminator:
                msg = f"{terminator!r} remains unmatched in {value!r}"
                raise MatchError(msg)
        args.append(last_arg)
        return [_flatten_string_fragments(a) for a in args], pos

    @classmethod
    def _escaped_fragment(cls, value: str, pos: int) -> str | None:
        if len(value) > pos + 1 and value[pos] == "\\":
            if value[pos + 1] in BACKSLASH_ESCAPE_CHARS:
                return cls._fragment(value, pos + 1, pos + 2)
            if value[pos + 1] == "\\":
                # Keep both backslashes for the later shlex pass.
                return cls._fragment(value, pos, pos + 2)
        return None

    @staticmethod
    def _next_special_position(value: str, pos: int, terminator: str, split: str | None) -> int:
        # Group plain text to avoid rebuilding origin spans per character.
        return min(
            (
                at
                for char in ("\\", REPLACE_START, "[", terminator, split)
                if char and (at := value.find(char, pos + 1)) >= 0
            ),
            default=len(value),
        )

    @staticmethod
    def _fragment(value: str, start: int, end: int | None = None) -> str:
        return value.fragment(start, end) if isinstance(value, HostText) else value[start:end]


def _flatten_string_fragments(fragments: Sequence[str | _OtherFragment]) -> list[str | _OtherFragment]:
    result: list[str | _OtherFragment] = []
    last_str: list[str] = []
    for obj in fragments:
        if isinstance(obj, str):
            last_str.append(obj)
        else:
            if last_str:
                result.append(HostText.from_parts(last_str))
                last_str = []
            result.append(obj)
    if last_str:
        result.append(HostText.from_parts(last_str))
    return result


class Replacer:
    # Recursively expand MatchExpression against the config and loader.
    def __init__(
        self,
        conf: Config,
        reference: ReplaceReference,
        conf_args: ConfigLoadArgs,
        depth: int = 0,
        *,
        recursive: bool = True,
    ) -> None:
        self.conf = conf
        self.reference = reference
        self.conf_args = conf_args
        self.depth = depth
        self.recursive = recursive
        self.program = False
        self.root: Replacer = self
        self.depth_exhausted: bool = False

    def __call__(self, value: MatchArg) -> Sequence[str]:
        result: Final[list[str]] = []
        for part in value:
            if isinstance(part, MatchExpression):
                if part.literal or self.root.depth_exhausted:
                    literal = self._literal_match(part)
                    result.append(HostText(literal, literal=part.literal) if part.host else literal)
                else:
                    result.append(self._replace_match(part)[0])
            else:
                result.append(part)
        return result

    @classmethod
    def _literal_match(cls, value: MatchExpression) -> str:
        args: Final[Iterator[str]] = (
            "".join(cls._literal_match(part) if isinstance(part, MatchExpression) else part for part in arg)
            for arg in value.expr
        )
        return f"{{{ARG_DELIMITER.join(args)}}}"

    def _replace_match(self, value: MatchExpression) -> tuple[str, bool]:
        flattened_args: Final[list[str]] = [self._flatten_arg(arg) for arg in value.expr]
        replace_value: Final[str | ConfigDefault | None] = self._replace_args(flattened_args)
        if replace_value is not None:
            return replace_value if isinstance(replace_value, str) else replace_value.text, True
        # Preserve unmatched braces for factor expressions such as {py39,py38}-{,dep}.
        literal: Final[str] = f"{REPLACE_START}{ARG_DELIMITER.join(flattened_args)}{REPLACE_END}"
        return HostText(literal) if value.host else literal, False

    def _flatten_arg(self, value: MatchArg) -> str:
        return self.join(value)

    def join(self, value: MatchArg) -> str:
        """Join the parts of a replaced value into one value.

        :param value: the parts to join

        :returns: the joined value
        """
        return HostText.from_parts(self(value))

    def _replace_args(self, flattened_args: list[str]) -> str | None:
        # Isolate chain updates from adjacent substitutions (#2869).
        conf_args: Final[ConfigLoadArgs] = self.conf_args.copy()
        replace_value: Final[str | ConfigDefault | None] = self._resolve_replace(
            flattened_args[0], flattened_args[1:], flattened_args, conf_args
        )
        if replace_value is not None and (
            self.recursive
            and not self.root.depth_exhausted
            and isinstance(replace_value, RawText)
            and any(
                isinstance(match, MatchExpression) and not match.literal for match in find_replace_expr(replace_value)
            )
        ):
            try:
                return self._nested(conf_args).expand(replace_value)
            except MatchRecursionError as error:
                LOGGER.warning(str(error))
        return replace_value.text if isinstance(replace_value, ConfigDefault) else replace_value

    def _resolve_replace(
        self, of_type: str, args: list[str], flattened_args: list[str], conf_args: ConfigLoadArgs
    ) -> str | ConfigDefault | None:
        if of_type == "/":
            return os.sep
        if not of_type and args == [""]:
            return os.pathsep
        dispatch: dict[str, Callable[[], str | ConfigDefault | None]] = {
            "env": lambda: _replace_env(self.conf, args, conf_args),
            "tty": lambda: replace_tty(args),
            "posargs": lambda: replace_pos_args(self.conf, args, conf_args, program_first=self.program),
            "glob": lambda: replace_glob(self.conf, args),
            "factor": lambda: (
                ConfigDefault(text=replace_factor(self.conf, args, conf_args), start=2)
                if not self.conf.factor_labels(conf_args.env_name)
                else replace_factor(self.conf, args, conf_args)
            ),
        }
        if handler := dispatch.get(of_type):
            return handler()
        return self.reference(HostText.from_parts(flattened_args, separator=ARG_DELIMITER), conf_args)

    def _nested(self, conf_args: ConfigLoadArgs) -> Self:
        nested: Final[Self] = type(self)(self.conf, self.reference, conf_args, self.depth + 1)
        nested.program = self.program
        nested.root = self.root
        return nested

    def expand(self, value: str | MatchExpression) -> str:
        """Resolve the replacements of a value, up to the maximum depth.

        :param value: the value to expand

        :returns: the value with its replacements resolved
        """
        if self.depth > MAX_REPLACE_DEPTH:
            self.root.depth_exhausted = True
        MatchRecursionError.check(self.depth, value)
        return self.join_value(find_replace_expr(value))

    def join_value(self, value: MatchArg) -> str:
        return self.join(value)


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ConfigDefault:
    """A default value of a replacement, with the span of the text it stands for.

    :param text: the default text
    :param start: the index where the text it stands for starts
    :param stop: the index where the text it stands for ends, ``None`` when it is open ended
    """

    text: str
    start: int
    stop: int | None = None

    @override
    def __str__(self) -> str:
        return self.text


class CommandLinesReplacer(Replacer):
    @override
    def join_value(self, value: MatchArg) -> str:
        parts: Final[Sequence[str | _Replaced]] = _flatten_string_fragments(list(self._split_replaced(value)))
        return self._join_replaced(parts)

    def _split_replaced(self, value: MatchArg) -> Iterator[str | _Replaced]:
        program: Final[bool] = self.program
        preceding: Final[list[str]] = []
        try:
            for part in value:
                self.program = program and self._within_program("".join(preceding))
                replaced_parts: list[str | _Replaced] = self._split_part(part)
                preceding.extend(map(str, replaced_parts))
                yield from replaced_parts
        finally:
            self.program = program

    @staticmethod
    def _within_program(text: str) -> bool:
        return not re.search(r"\S\s", text.rpartition("\n")[2].lstrip().lstrip("-!"))

    def _split_part(self, part: str | MatchExpression) -> list[str | _Replaced]:
        if not isinstance(part, MatchExpression):
            return [part]
        if part.literal or self.root.depth_exhausted:
            return [self._literal_match(part)]
        args: Final[list[list[str | _Replaced]]] = [list(self._split_replaced(arg)) for arg in part.expr]
        flattened_args: Final[list[str]] = ["".join(map(str, arg)) for arg in args]
        conf_args: Final[ConfigLoadArgs] = self.conf_args.copy()
        replaced: Final[str | ConfigDefault | None] = self._resolve_replace(
            flattened_args[0], flattened_args[1:], flattened_args, conf_args
        )
        if isinstance(replaced, ConfigDefault):
            default_parts: Final[list[str | _Replaced]] = []
            for at, arg in enumerate(args[replaced.start : replaced.stop]):
                if at:
                    default_parts.append(ARG_DELIMITER)
                default_parts.extend(arg)
            return default_parts
        if (expanded := self._expand_raw(replaced, conf_args)) is not None:
            return [expanded]
        if replaced is not None:
            quoted_text: Final[str | None] = (
                " ".join(pos_args)
                if flattened_args[0] == "posargs"
                and (pos_args := load_posargs(self.conf, self.conf_args, program_first=self.program)) is not None
                else None
            )
            return [_Replaced(text=replaced, quoted_text=quoted_text)]
        unresolved_parts: Final[list[str | _Replaced]] = [REPLACE_START]
        for at, arg in enumerate(args):
            if at:
                unresolved_parts.append(ARG_DELIMITER)
            unresolved_parts.extend(arg)
        unresolved_parts.append(REPLACE_END)
        return unresolved_parts

    def _expand_raw(self, replaced: str | None, conf_args: ConfigLoadArgs) -> _Replaced | None:
        if not (
            self.recursive
            and isinstance(replaced, RawText)
            and any(isinstance(match, MatchExpression) and not match.literal for match in find_replace_expr(replaced))
        ):
            return None
        nested: Final[CommandLinesReplacer] = self._nested(conf_args)
        if nested.depth > MAX_REPLACE_DEPTH:
            self.root.depth_exhausted = True
        try:
            MatchRecursionError.check(nested.depth, replaced)
        except MatchRecursionError as error:
            LOGGER.warning(str(error))
            return None
        nested_parts: Final[Sequence[str | _Replaced]] = _flatten_string_fragments(
            list(nested._split_replaced(find_replace_expr(replaced)))  # ruff:ignore[private-member-access]  # own class
        )
        return _Replaced(
            text=nested._join_replaced(nested_parts),  # ruff:ignore[private-member-access]  # same class
            quoted_text="".join(
                part.quoted_text if isinstance(part, _Replaced) and part.quoted_text is not None else str(part)
                for part in nested_parts
            ),
        )

    def _join_replaced(self, parts: Sequence[str | _Replaced]) -> str:
        result: Final[list[str]] = []
        quote = ""
        for at, part in enumerate(parts):
            if isinstance(part, _Replaced):
                text = self._replaced_text(part, quote, parts, at)
                if quote:
                    result.append(self._escape_within_quote(quote, text))
                    continue
            else:
                text = str(part)
            quote = self._open_quote(quote, text)
            result.append(text)
        return "".join(result)

    def _replaced_text(self, part: _Replaced, quote: str, parts: Sequence[str | _Replaced], at: int) -> str:
        text = part.quoted_text if quote and part.quoted_text is not None else str(part)
        if not quote and isinstance(part.text, Arguments):
            text = "\n".join(quote_args([line]) if line else line for line in part.text.split("\n"))
        elif not quote and isinstance(part.text, _GlobMatches):
            text = quote_args(part.text.matches)
        if quote or self._shares_line(parts, at):
            text = " ".join(text.splitlines())
        return text

    @staticmethod
    def _shares_line(value: Sequence[str | _Replaced], at: int) -> bool:
        before: Final[str | _Replaced] = value[at - 1] if at else ""
        after: Final[str | _Replaced] = value[at + 1] if at + 1 < len(value) else ""
        if isinstance(before, _Replaced) or isinstance(after, _Replaced):
            return True
        return bool(before.rpartition("\n")[2].strip() or after.partition("\n")[0].strip())

    @staticmethod
    def _escape_within_quote(quote: str, text: str) -> str:
        if quote == "'":
            return text.replace("'", "'\"'\"'")
        # escaped comments are restored before command splitting
        return re.sub(r'\\(?!\#)|"', r"\\\g<0>", text)

    @staticmethod
    def _open_quote(quote: str, text: str) -> str:
        escaped = False
        for char in text:
            if char == "\n":
                quote, escaped = "", False
            elif escaped:
                escaped = False
            elif char == "\\" and quote != "'":
                escaped = True
            elif char == quote:
                quote = ""
            elif not quote and char in {"'", '"'}:
                quote = char
        return quote


class Arguments(str):  # ruff:ignore[subclass-builtin]  # keep argument values distinct from command text
    """Text of replacement arguments, kept apart from the command text they are part of."""

    __slots__ = ()


class _GlobMatches(str):  # ruff:ignore[subclass-builtin]  # retain match boundaries through substitution
    __slots__ = ("matches",)
    matches: tuple[str, ...]

    def __new__(cls, matches: Sequence[str]) -> Self:
        result = super().__new__(cls, " ".join(matches))
        result.matches = tuple(matches)
        return result


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _Replaced:
    text: str
    quoted_text: str | None

    @override
    def __str__(self) -> str:
        return self.text


class RequirementLinesReplacer(Replacer):
    def __init__(
        self,
        conf: Config,
        reference: ReplaceReference,
        conf_args: ConfigLoadArgs,
        depth: int = 0,
        *,
        callbacks: RequirementLineCallbacks,
    ) -> None:
        super().__init__(conf, reference, conf_args, depth)
        self._callbacks = callbacks

    @override
    def _resolve_replace(
        self, of_type: str, args: list[str], flattened_args: list[str], conf_args: ConfigLoadArgs
    ) -> str | ConfigDefault | None:
        value: Final[str | ConfigDefault | None] = super()._resolve_replace(of_type, args, flattened_args, conf_args)
        # pip's ${NAME} syntax belongs to the configuration, a host variable's value reaches pip as written
        return value.protect(self._callbacks.protect_host_value) if isinstance(value, HostText) else value

    @override
    def _flatten_arg(self, value: MatchArg) -> str:
        return self.join_value(value)

    @override
    def join_value(self, value: MatchArg) -> str:
        replaced: Final[Sequence[str]] = self(value)
        baseline: Final[list[str]] = list(replaced)
        for at, part in enumerate(value):
            if not isinstance(part, MatchExpression):
                continue
            text = replaced[at]
            following = "".join(replaced[at + 1 :])
            if re.search(rf"\\(?={_REQUIREMENT_LINE_BREAKS})", text) or (
                text.endswith("\\") and (not following or re.match(_REQUIREMENT_LINE_BREAKS, following))
            ):
                msg = "a requirement substitution cannot end a line with a backslash"
                raise ValueError(msg)
            if (shares_line := self._shares_line(value, at)) and text != "".join(text.splitlines()):
                msg = "a substitution within a requirement cannot add a line break"
                raise ValueError(msg)
            if shares_line:
                baseline[at] = f"\x00{at}\x00"
        result: Final[str] = "".join(replaced)
        if baseline != replaced:
            self._callbacks.validate_options("".join(baseline), result)
        return result

    @staticmethod
    def _shares_line(value: MatchArg, at: int) -> bool:
        for part in reversed(value[:at]):
            if isinstance(part, MatchExpression) or re.split(_REQUIREMENT_LINE_BREAKS, part)[-1].strip():
                return True
            if re.search(_REQUIREMENT_LINE_BREAKS, part):
                break
        for part in value[at + 1 :]:
            if isinstance(part, MatchExpression) or re.split(_REQUIREMENT_LINE_BREAKS, part)[0].strip():
                return True
            if re.search(_REQUIREMENT_LINE_BREAKS, part):
                break
        return False

    @override
    def _nested(self, conf_args: ConfigLoadArgs) -> Self:
        nested: Final[Self] = type(self)(
            self.conf, self.reference, conf_args, self.depth + 1, callbacks=self._callbacks
        )
        nested.root = self.root
        return nested


class HostText(RawText):
    """Text that keeps track of the spans that came from the configuration and of its literal spans.

    :ivar spans: the spans of the text that came from the configuration
    :ivar literal_spans: the spans of the text that is taken literally
    """

    __slots__ = ("literal_spans", "spans")
    spans: tuple[tuple[int, int], ...]
    literal_spans: tuple[tuple[int, int], ...]

    def __new__(
        cls,
        value: str,
        *,
        spans: tuple[tuple[int, int], ...] | None = None,
        literal_spans: tuple[tuple[int, int], ...] = (),
        literal: bool = False,
    ) -> Self:
        result: Final[Self] = super().__new__(cls, value)
        result.spans = ((0, len(value)),) if spans is None else spans
        result.literal_spans = ((0, len(value)),) if literal else literal_spans
        return result

    @override
    def splitlines(self, keepends: bool = False) -> list[str]:
        lines: Final[list[str]] = []
        offset = 0
        for line in super().splitlines(keepends=True):
            line_length: int = len(line) if keepends else len(line.rstrip("\r\n\v\f\x1c\x1d\x1e\x85\u2028\u2029"))
            lines.append(self.fragment(offset, offset + line_length))
            offset += len(line)
        return lines

    def fragment(self, start: int, end: int | None = None) -> str:
        """Get a part of the text, keeping the spans that fall within it.

        :param start: the start index of the part
        :param end: the end index of the part, the end of the text when ``None``

        :returns: the part of the text
        """
        stop: Final[int] = len(self) if end is None else end
        spans: Final[tuple[tuple[int, int], ...]] = self._fragment_spans(self.spans, start, stop)
        value: Final[str] = super().__getitem__(slice(start, stop))
        return (
            HostText(value, spans=spans, literal_spans=self._fragment_spans(self.literal_spans, start, stop))
            if spans
            else value
        )

    @staticmethod
    def _fragment_spans(spans: tuple[tuple[int, int], ...], start: int, stop: int) -> tuple[tuple[int, int], ...]:
        return tuple(
            (max(span_start, start) - start, min(span_end, stop) - start)
            for span_start, span_end in spans
            if span_start < stop and span_end > start
        )

    @override
    def strip(self, chars: str | None = None) -> str:
        return self.fragment(len(self) - len(super().lstrip(chars)), len(super().rstrip(chars)))

    def covers(self, end: int) -> bool:
        """Check whether the first span covers the text up to an index.

        :param end: the index to check up to

        :returns: whether the first span covers the text up to that index
        """
        return self.spans[0][0] == 0 and self.spans[0][1] >= end

    def covers_literal(self, end: int) -> bool:
        """Check whether the first literal span covers the text up to an index.

        :param end: the index to check up to

        :returns: whether the first literal span covers the text up to that index
        """
        return bool(self.literal_spans) and self.literal_spans[0][0] == 0 and self.literal_spans[0][1] >= end

    def protect(self, protector: _HostValueProtector) -> str:
        """Protect the spans of the text that came from the configuration, so they are not replaced again.

        :param protector: the protector that escapes the text

        :returns: the protected text
        """
        parts: Final[list[str]] = []
        offset = 0
        for start, end in self.spans:
            literal_spans = tuple(
                (len(protector(self[start:literal_start])), len(protector(self[start:literal_end])))
                for literal_start, literal_end in self.literal_spans
                if start <= literal_start and literal_end <= end
            )
            parts.extend((self[offset:start], HostText(protector(self[start:end]), literal_spans=literal_spans)))
            offset = end
        parts.append(self[offset:])
        return HostText.from_parts(parts)

    @classmethod
    def from_parts(cls, parts: Sequence[str], *, separator: str = "") -> str:
        """Join parts into one text, keeping the spans of the parts that are host text.

        :param parts: the parts to join
        :param separator: the text placed between two parts

        :returns: the joined text
        """
        spans: list[tuple[int, int]] = []
        literal_spans: list[tuple[int, int]] = []
        offset = 0
        for index, part in enumerate(parts):
            if isinstance(part, HostText):
                for part_spans, joined_spans in ((part.spans, spans), (part.literal_spans, literal_spans)):
                    for start, end in part_spans:
                        absolute_start, absolute_end = offset + start, offset + end
                        if joined_spans and joined_spans[-1][1] == absolute_start:
                            joined_spans[-1] = joined_spans[-1][0], absolute_end
                        else:
                            joined_spans.append((absolute_start, absolute_end))
            offset += len(part) + (len(separator) if index + 1 < len(parts) else 0)
        joined: Final[str] = separator.join(parts)
        return cls(joined, spans=tuple(spans), literal_spans=tuple(literal_spans)) if spans else joined


class _RequirementOptionsValidator(Protocol):
    def __call__(self, source: str, expanded: str, /) -> None: ...


class _HostValueProtector(Protocol):
    def __call__(self, value: str, /) -> str: ...


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class RequirementLineCallbacks:
    """Callbacks that validate the options of a requirement line and protect its host values.

    :param validate_options: the callback that validates the options of a requirement line
    :param protect_host_value: the callback that protects the text that came from the configuration
    """

    validate_options: _RequirementOptionsValidator
    protect_host_value: _HostValueProtector


class EntriesReplacer(Replacer):
    def __init__(
        self,
        conf: Config,
        reference: ReplaceReference,
        conf_args: ConfigLoadArgs,
        depth: int = 0,
        *,
        separators: str = ",\n",
    ) -> None:
        super().__init__(conf, reference, conf_args, depth)
        self.separators = separators

    @override
    def __call__(self, value: MatchArg) -> Sequence[str]:
        replaced: Final[list[tuple[str, bool]]] = [
            ((self._literal_match(part), False) if self.root.depth_exhausted else self._replace_match(part))
            if isinstance(part, MatchExpression)
            else (part, False)
            for part in value
        ]
        for at, (text, resolved) in enumerate(replaced):
            if resolved and self._shares_entry(value, at) and any(char in text for char in self.separators):
                msg = "a substitution within an entry cannot add an entry separator"
                raise ValueError(msg)
        return [text for text, _ in replaced]

    def _shares_entry(self, value: MatchArg, at: int) -> bool:
        return self._has_text(reversed(value[:at]), -1) or self._has_text(value[at + 1 :], 0)

    def _has_text(self, parts: Iterable[str | MatchExpression], side: int) -> bool:
        for part in parts:
            if isinstance(part, MatchExpression):
                return True
            text = re.split(f"[{self.separators}]", part)[side]
            if text.strip():
                return True
            if text != part:
                return False
        return False

    @override
    def join_value(self, value: MatchArg) -> str:
        if self.separators == ",\n" and any("\n" in part for part in value if isinstance(part, str)):
            self.separators = "\n"  # A comma is data when the author chose line-separated entries.
        return super().join_value(value)

    @override
    def _nested(self, conf_args: ConfigLoadArgs) -> Self:
        nested: Final[Self] = super()._nested(conf_args)
        nested.separators = self.separators
        return nested


def replace_pos_args(
    conf: Config, args: list[str], conf_args: ConfigLoadArgs, *, program_first: bool
) -> str | ConfigDefault:
    pos_args = load_posargs(conf, conf_args, program_first=program_first)
    return (
        ConfigDefault(text=HostText.from_parts(args, separator=ARG_DELIMITER), start=1)
        if pos_args is None
        else quote_args(pos_args)
    )


def quote_args(args: Sequence[str]) -> str:
    # INI settings split lines before parsing quotes.
    """Quote the arguments so they can be split back into the same arguments.

    :param args: the arguments to quote

    :returns: the arguments as a single command line
    """
    normalized: Final[list[str]] = [" ".join(arg.splitlines()) for arg in args]
    if sys.platform != "win32":
        return shlex.join(normalized)
    # Windows command splitting keeps a lone backslash, so paths stay unquoted where a value is not split into a command
    return " ".join(arg if arg and not re.search(r"[\s'\"]|\\\\", arg) else shlex.quote(arg) for arg in normalized)


def load_posargs(conf: Config, conf_args: ConfigLoadArgs, *, program_first: bool) -> tuple[str, ...] | None:
    """Get the positional arguments, with paths relative to the change directory when the environment expects paths.

    :param conf: the global config
    :param conf_args: env args
    :param program_first: whether the program comes before the positional arguments

    :returns: the positional arguments, or ``None`` when none were given
    """
    to_path: Path | None = None
    if conf_args.env_name is not None:  # pragma: no branch  # other outcome untested
        env_conf = conf.get_env(conf_args.env_name)
        try:
            # other outcome untested
            if env_conf["args_are_paths"] and not any(
                entry.endswith(".change_dir") for entry in conf_args.chain
            ):  # pragma: no branch
                to_path = env_conf.get("change_dir", Path)
        except KeyError:
            pass
    return conf.pos_args(to_path, program_first=program_first)


def replace_env(conf: Config | None, args: list[str], conf_args: ConfigLoadArgs) -> str:
    """Replace an environment variable reference with its value.

    :param conf: the global config, ``None`` when unknown
    :param args: the arguments of the reference, the variable name first and its default after
    :param conf_args: env args

    :returns: the value of the variable, or its default
    """
    value: Final[str | ConfigDefault] = _replace_env(conf, args, conf_args)
    # Keep host-value provenance for inline requirement parsing.
    return value if isinstance(value, str) else str(value)


def _replace_env(conf: Config | None, args: list[str], conf_args: ConfigLoadArgs) -> str | ConfigDefault:
    if not args or not args[0]:
        msg = "No variable name was supplied in {env} substitution"
        raise MatchError(msg)
    key = args[0]
    new_key = f"env:{key}"

    if conf is not None and conf_args.env_name is not None:  # on core no set env support # pragma: no branch
        if new_key not in conf_args.chain:  # check if set env
            if (value := _load_set_env(conf, conf_args.env_name, conf_args, key)) is not None:
                return value
        elif conf_args.chain[-1] != new_key:  # if there's a chain but only self-refers than use os.environ
            circular = ", ".join(i[4:] for i in conf_args.chain[conf_args.chain.index(new_key) :])
            msg = f"circular chain between set env {circular}"
            raise MatchRecursionError(msg)

    if key in os.environ:
        return HostText(os.environ[key])  # a host variable has always been allowed to hold tokens of its own

    return ConfigDefault(text=HostText.from_parts(args[1:], separator=ARG_DELIMITER), start=2)


def _load_set_env(conf: Config, env_name: str, conf_args: ConfigLoadArgs, key: str) -> str | None:
    conf_args.chain.append(f"env:{key}")
    env_conf = conf.get_env(env_name)
    try:
        set_env: SetEnv = env_conf.load("set_env", chain=conf_args.chain)
    except CircularChainError:
        if not (
            conf_args.chain[-1].endswith(".set_env") and any(i.endswith(".set_env") for i in conf_args.chain[:-1])
        ):  # pragma: no branch  # other outcome untested
            raise
        return None
    if key in set_env:
        return set_env.load(key, conf_args)
    return None


def replace_tty(args: list[str]) -> ConfigDefault:
    selected: Final[int] = 0 if sys.stdout.isatty() else 1
    return ConfigDefault(
        text=args[selected] if len(args) > selected else "",
        start=selected + 1,
        stop=selected + 2,
    )


def replace_glob(conf: Config | None, args: list[str]) -> str | ConfigDefault:
    if not args or not args[0]:
        msg = "No pattern was supplied in glob substitution"
        raise MatchError(msg)
    # rejoin Windows drive letter that was split on colon (e.g. C:\path -> ["C", "\\path"])
    is_win_drive: Final[bool] = (
        sys.platform == "win32"
        and len(args[0]) == 1
        and args[0].isalpha()
        and len(args) > 1
        and args[1][:1] in {"\\", "/"}
    )
    if is_win_drive:
        pattern = f"{args[0]}:{args[1]}"
        default_args = args[2:]
    else:
        pattern = args[0]
        default_args = args[1:]
    if conf is not None and not Path(pattern).is_absolute():
        pattern = str(Path(glob.escape(str(conf.core["tox_root"]))) / pattern)
    if matches := sorted(glob.glob(pattern, recursive=True)):  # ruff:ignore[glob]  # matches user pattern
        return _GlobMatches(matches)
    return ConfigDefault(
        text=HostText.from_parts(default_args, separator=ARG_DELIMITER), start=3 if is_win_drive else 2
    )


def replace_factor(conf: Config, args: list[str], conf_args: ConfigLoadArgs) -> str:
    """Replace a factor reference with the value of its factor label.

    :param conf: the global config
    :param args: the arguments of the reference, the label first and its default after
    :param conf_args: env args

    :returns: the value of the label for the environment, or its default

    :raises MatchError: when no factor label was supplied
    """
    if not args or not args[0]:
        msg = "No label was supplied in {factor} substitution"
        raise MatchError(msg)
    label = args[0]
    default = HostText.from_parts(args[1:], separator=ARG_DELIMITER) if len(args) > 1 else None
    group = conf.factor_labels(conf_args.env_name).get(label)
    if group is None or conf_args.env_name is None:
        return default or ""
    if (override := os.environ.get(f"{_FACTOR_ENV_PREFIX}{label}")) is not None:
        return HostText(override, literal=True)
    env_factors = set(conf_args.env_name.split("-"))
    for value in group.values:
        if value in env_factors:
            return value
    return default if default is not None else group.default or ""


__all__ = [
    "MAX_REPLACE_DEPTH",
    "Arguments",
    "ConfigDefault",
    "HostText",
    "MatchArg",
    "MatchError",
    "MatchExpression",
    "MatchRecursionError",
    "RawText",
    "ReplaceReference",
    "RequirementLineCallbacks",
    "find_replace_expr",
    "load_posargs",
    "quote_args",
    "replace",
    "replace_command_lines",
    "replace_entries",
    "replace_env",
    "replace_factor",
    "replace_for",
    "replace_once",
    "replace_program",
    "replace_requirement_lines",
]
