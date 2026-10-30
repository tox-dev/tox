"""Apply value substitution (replacement) on tox strings."""

from __future__ import annotations

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
from typing import TYPE_CHECKING, Any, Final, Union, get_args, get_origin

from tox.config.types import CircularChainError, Command, EnvList
from tox.util.typing_compat import override

if TYPE_CHECKING:
    from types import UnionType
    from typing import Self

    from tox.config.loader.api import ConfigLoadArgs
    from tox.config.main import Config
    from tox.config.set_env import SetEnv


LOGGER = logging.getLogger(__name__)

# split alongside :, unless it is preceded by a single capital letter (Windows drive letters in paths)
ARG_DELIMITER: Final[str] = ":"
REPLACE_START: Final[str] = "{"
REPLACE_END: Final[str] = "}"
BACKSLASH_ESCAPE_CHARS: Final[tuple[str, ...]] = (ARG_DELIMITER, REPLACE_START, REPLACE_END, "[", "]")
MAX_REPLACE_DEPTH: Final[int] = 100
# Factor overrides can supply values absent from the configuration without renaming environments.
_FACTOR_ENV_PREFIX: Final[str] = "TOX_FACTOR_"
_REQUIREMENT_LINE_BREAKS: Final[str] = r"[\n\r\v\f\x1c-\x1e\x85\u2028\u2029]"


class MatchRecursionError(ValueError):
    """Could not stabilize on replacement value."""

    @staticmethod
    def check(depth: int, value: Any) -> None:
        if depth > MAX_REPLACE_DEPTH:
            msg = f"Could not expand {value} after recursing {depth} frames"
            raise MatchRecursionError(msg)


class MatchError(Exception):
    """Couldn't find end terminator in MatchExpression."""


class RawText(str):  # ruff:ignore[subclass-builtin] # keep the origin through the str replacement interface
    __slots__ = ()


class ReplaceReference(ABC):
    @abstractmethod
    def __call__(self, value: str, conf_args: ConfigLoadArgs) -> str | None:
        """Perform a reference replacement.

        :param value: the raw value
        :param conf_args: the configuration loads argument object

        :returns: the replaced value (as :class:`RawText` to have its own tokens replaced), None if it can't do it.

        """
        raise NotImplementedError


MatchArg = Sequence[Union[str, "MatchExpression"]]


def find_replace_expr(value: str | MatchExpression) -> MatchArg:
    """Find all replaceable tokens within value."""
    if isinstance(value, MatchExpression):
        return [value]
    return MatchExpression.parse_and_split_to_terminator(value)[0][0]


def replace(
    conf: Config, reference: ReplaceReference, value: str | MatchExpression, args: ConfigLoadArgs, depth: int = 0
) -> str:
    """Replace all active tokens within value according to the config."""
    return Replacer(conf, reference, conf_args=args, depth=depth).expand(value)


def replace_command_lines(
    conf: Config, reference: ReplaceReference, value: str | MatchExpression, args: ConfigLoadArgs
) -> str:
    """Replace all active tokens within value, where each line of value is one command."""
    replacer: Final[CommandLinesReplacer] = CommandLinesReplacer(conf, reference, conf_args=args)
    replacer.program = True
    return replacer.expand(value)


def replace_program(conf: Config, reference: ReplaceReference, value: str, args: ConfigLoadArgs) -> str:
    replacer: Final[Replacer] = Replacer(conf, reference, conf_args=args)
    replacer.program = True
    return replacer.expand(value)


def replace_requirement_lines(
    conf: Config, reference: ReplaceReference, value: str | MatchExpression, args: ConfigLoadArgs
) -> str:
    return RequirementLinesReplacer(conf, reference, conf_args=args).expand(value)


def replace_entries(
    conf: Config,
    reference: ReplaceReference,
    value: str | MatchExpression,
    args: ConfigLoadArgs,
    *,
    separators: str = ",\n",
) -> str:
    return EntriesReplacer(conf, reference, conf_args=args, separators=separators).expand(value)


def replace_for(
    of_type: type[object] | UnionType,
) -> Callable[[Config, ReplaceReference, str | MatchExpression, ConfigLoadArgs], str]:
    kinds: Final[set[type[object] | UnionType]] = {get_origin(kind) or kind for kind in (of_type, *get_args(of_type))}
    if of_type == list[Command]:
        return replace
    if EnvList in kinds:
        return partial(replace_entries, separators=",\n{}")
    if dict in kinds:
        return partial(replace_entries, separators="\n")
    if kinds & {list, set}:
        return replace_entries
    return replace


def replace_once(conf: Config, reference: ReplaceReference, value: str | MatchExpression, args: ConfigLoadArgs) -> str:
    """Replace the active tokens within value, but not the tokens within the text they are replaced with."""
    return Replacer(conf, reference, conf_args=args, recursive=False).join(find_replace_expr(value))


class MatchExpression:  # ruff:ignore[eq-without-hash]
    """An expression that is handled specially by the Replacer."""

    def __init__(self, expr: Sequence[MatchArg], term_pos: int | None = None) -> None:
        self.expr = expr
        self.term_pos = term_pos

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
        """Process a curly brace replacement expression."""
        if value.startswith("[]"):
            # `[]` is shorthand for `{posargs}`
            return MatchExpression(expr=[["posargs"]], term_pos=1)
        if not value.startswith(REPLACE_START):
            return None
        try:
            # recursively handle inner expression
            rec_expr, term_pos = cls.parse_and_split_to_terminator(
                value[1:],
                terminator=REPLACE_END,
                split=ARG_DELIMITER,
            )
        except MatchError:
            # didn't find the expected terminator character, so treat `{` as if escaped.
            pass
        else:
            return MatchExpression(expr=rec_expr, term_pos=term_pos)
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

        """
        args = []
        last_arg: list[str | MatchExpression] = []
        pos = 0

        while pos < len(value):
            if len(value) > pos + 1 and value[pos] == "\\":
                if value[pos + 1] in BACKSLASH_ESCAPE_CHARS:
                    last_arg.append(value[pos + 1])
                    pos += 2
                    continue
                if value[pos + 1] == "\\":
                    # Keep both backslashes for the later shlex pass.
                    last_arg.append(value[pos : pos + 2])
                    pos += 2
                    continue
            fragment = value[pos:]
            if terminator and fragment.startswith(terminator):
                pos += len(terminator)
                break
            if split and fragment.startswith(split):
                # found a new argument
                args.append(last_arg)
                last_arg = []
                pos += len(split)
                continue
            expr = cls._next_replace_expression(fragment)
            if expr is not None:
                pos += (expr.term_pos or 0) + 1
                last_arg.append(expr)
                continue
            # default case: consume the next character
            last_arg.append(value[pos])
            pos += 1
        else:  # fell out of the loop
            if terminator:
                msg = f"{terminator!r} remains unmatched in {value!r}"
                raise MatchError(msg)
        args.append(last_arg)
        return [_flatten_string_fragments(a) for a in args], pos


def _flatten_string_fragments(seq_of_str_or_other: Sequence[str | Any]) -> Sequence[str | Any]:
    """Join runs of contiguous str values in a sequence; nny non-str items in the sequence are left as-is."""
    result = []
    last_str = []
    for obj in seq_of_str_or_other:
        if isinstance(obj, str):
            last_str.append(obj)
        else:
            if last_str:
                result.append("".join(last_str))
                last_str = []
            result.append(obj)
    if last_str:
        result.append("".join(last_str))
    return result


class Replacer:
    """Recursively expand MatchExpression against the config and loader."""

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
                result.append(self._literal_match(part) if self.root.depth_exhausted else self._replace_match(part)[0])
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

    def join(self, value: MatchArg) -> str:
        return "".join(self(value))

    def expand(self, value: str | MatchExpression) -> str:
        if self.depth > MAX_REPLACE_DEPTH:
            self.root.depth_exhausted = True
        MatchRecursionError.check(self.depth, value)
        return self.join_value(find_replace_expr(value))

    def join_value(self, value: MatchArg) -> str:
        return self.join(value)

    def _replace_match(self, value: MatchExpression) -> tuple[str, bool]:
        # Keep substitutions from sharing a mutated chain (#2869).
        conf_args = self.conf_args.copy()
        flattened_args = [self._flatten_arg(arg) for arg in value.expr]
        of_type, *args = flattened_args
        replace_value = self._resolve_replace(of_type, args, flattened_args, conf_args)
        if replace_value is not None:
            # Only raw configuration text gets another pass; positional arguments and file names are data.
            if (
                self.recursive
                and not self.root.depth_exhausted
                and isinstance(replace_value, RawText)
                and any(isinstance(match, MatchExpression) for match in find_replace_expr(replace_value))
            ):
                try:
                    return self._nested(conf_args).expand(replace_value), True
                except MatchRecursionError as err:
                    LOGGER.warning(str(err))
                    return replace_value, True
            return replace_value, True
        # Factor expressions such as {py39,py38}-{,dep} also use braces.
        return f"{REPLACE_START}{ARG_DELIMITER.join(flattened_args)}{REPLACE_END}", False

    def _nested(self, conf_args: ConfigLoadArgs) -> Self:
        nested: Final[Self] = type(self)(self.conf, self.reference, conf_args, self.depth + 1)
        nested.program = self.program
        nested.root = self.root
        return nested

    def _flatten_arg(self, value: MatchArg) -> str:
        return self.join(value)

    def _resolve_replace(
        self, of_type: str, args: list[str], flattened_args: list[str], conf_args: ConfigLoadArgs
    ) -> str | None:
        if of_type == "/":
            return os.sep
        if not of_type and args == [""]:
            return os.pathsep
        dispatch: dict[str, Callable[[], str | None]] = {
            "env": lambda: replace_env(self.conf, args, conf_args),
            "tty": lambda: replace_tty(args),
            "posargs": lambda: replace_pos_args(self.conf, args, conf_args, program_first=self.program),
            "glob": lambda: replace_glob(self.conf, args),
            "factor": lambda: replace_factor(self.conf, args, conf_args),
        }
        if handler := dispatch.get(of_type):
            return handler()
        return self.reference(ARG_DELIMITER.join(flattened_args), conf_args)


class CommandLinesReplacer(Replacer):
    """Expand a value holding one command per line.

    A token alone on its line may expand into several commands, while a token sharing its line with other text joins its
    lines into that one command.

    """

    @override
    def __call__(self, value: MatchArg) -> Sequence[str]:
        outer_program: Final[bool] = self.program
        parts: Final[list[str]] = []
        for part in value:
            if isinstance(part, MatchExpression):
                self.program = outer_program and self._within_program("".join(parts))
                parts.append(self._literal_match(part) if self.root.depth_exhausted else self._replace_match(part)[0])
            else:
                parts.append(str(part))
        self.program = outer_program
        return parts

    @staticmethod
    def _within_program(text: str) -> bool:
        return not re.search(r"\S\s", text.rpartition("\n")[2].lstrip().lstrip("-!"))

    @override
    def join_value(self, value: MatchArg) -> str:
        return "".join(
            " ".join(replaced.splitlines()) if _shares_line(value, at) else replaced
            for at, replaced in enumerate(self(value))
        )


class RequirementLinesReplacer(Replacer):
    @override
    def _flatten_arg(self, value: MatchArg) -> str:
        return self.join_value(value)

    @override
    def join_value(self, value: MatchArg) -> str:
        replaced: Final[Sequence[str]] = self(value)
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
            if self._shares_line(value, at) and text != "".join(text.splitlines()):
                msg = "a substitution within a requirement cannot add a line break"
                raise ValueError(msg)
        return "".join(replaced)

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


def _shares_line(value: MatchArg, at: int) -> bool:
    if not isinstance(value[at], MatchExpression):
        return False
    before = value[at - 1] if at else ""
    after = value[at + 1] if at + 1 < len(value) else ""
    if isinstance(before, MatchExpression) or isinstance(after, MatchExpression):
        return True
    return bool(before.rpartition("\n")[2].strip() or after.partition("\n")[0].strip())


def replace_pos_args(conf: Config, args: list[str], conf_args: ConfigLoadArgs, *, program_first: bool) -> str:
    pos_args = load_posargs(conf, conf_args, program_first=program_first)
    return ARG_DELIMITER.join(args) if pos_args is None else quote_args(pos_args)


def quote_args(args: Sequence[str]) -> str:
    # INI settings split lines before parsing quotes.
    normalized: Final[list[str]] = [" ".join(arg.splitlines()) for arg in args]
    if sys.platform != "win32":
        return shlex.join(normalized)
    # Windows command splitting keeps a lone backslash, so paths stay unquoted where a value is not split into a command
    return " ".join(arg if arg and not re.search(r"[\s'\"]|\\\\", arg) else shlex.quote(arg) for arg in normalized)


def load_posargs(conf: Config, conf_args: ConfigLoadArgs, *, program_first: bool) -> tuple[str, ...] | None:
    to_path: Path | None = None
    if conf_args.env_name is not None:  # pragma: no branch
        env_conf = conf.get_env(conf_args.env_name)
        try:
            if env_conf["args_are_paths"] and not _loading_change_dir(conf_args):  # pragma: no branch
                to_path = env_conf.get("change_dir", Path)
        except KeyError:
            pass
    return conf.pos_args(to_path, program_first=program_first)


def _loading_change_dir(conf_args: ConfigLoadArgs) -> bool:
    return any(entry.endswith(".change_dir") for entry in conf_args.chain)


def replace_env(conf: Config | None, args: list[str], conf_args: ConfigLoadArgs) -> str:
    if not args or not args[0]:
        msg = "No variable name was supplied in {env} substitution"
        raise MatchError(msg)
    key = args[0]
    new_key = f"env:{key}"

    if conf is not None and conf_args.env_name is not None:  # on core no set env support # pragma: no branch
        if new_key not in conf_args.chain:  # check if set env
            conf_args.chain.append(new_key)
            env_conf = conf.get_env(conf_args.env_name)
            try:
                set_env: SetEnv = env_conf.load("set_env", chain=conf_args.chain)
            except CircularChainError:
                if not (
                    conf_args.chain[-1].endswith(".set_env")
                    and any(i.endswith(".set_env") for i in conf_args.chain[:-1])
                ):  # pragma: no branch
                    raise
            else:
                if key in set_env:
                    return set_env.load(key, conf_args)
        elif conf_args.chain[-1] != new_key:  # if there's a chain but only self-refers than use os.environ
            circular = ", ".join(i[4:] for i in conf_args.chain[conf_args.chain.index(new_key) :])
            msg = f"circular chain between set env {circular}"
            raise MatchRecursionError(msg)

    if key in os.environ:
        return RawText(os.environ[key])  # a host variable has always been allowed to hold tokens of its own

    return "" if len(args) == 1 else ARG_DELIMITER.join(args[1:])


def replace_tty(args: list[str]) -> str:
    return (args[0] if len(args) > 0 else "") if sys.stdout.isatty() else args[1] if len(args) > 1 else ""


def replace_glob(conf: Config | None, args: list[str]) -> str:
    if not args or not args[0]:
        msg = "No pattern was supplied in glob substitution"
        raise MatchError(msg)
    # rejoin Windows drive letter that was split on colon (e.g. C:\path -> ["C", "\\path"])
    if (
        sys.platform == "win32"
        and len(args[0]) == 1
        and args[0].isalpha()
        and len(args) > 1
        and args[1][:1] in {"\\", "/"}
    ):
        pattern = f"{args[0]}:{args[1]}"
        default_args = args[2:]
    else:
        pattern = args[0]
        default_args = args[1:]
    if conf is not None and not Path(pattern).is_absolute():
        pattern = str(conf.core["tox_root"] / pattern)
    if matches := sorted(glob.glob(pattern, recursive=True)):  # ruff:ignore[glob]
        return " ".join(matches)
    return ARG_DELIMITER.join(default_args) if default_args else ""


def replace_factor(conf: Config, args: list[str], conf_args: ConfigLoadArgs) -> str:
    if not args or not args[0]:
        msg = "No label was supplied in {factor} substitution"
        raise MatchError(msg)
    label = args[0]
    default = ARG_DELIMITER.join(args[1:]) if len(args) > 1 else None
    group = conf.factor_labels(conf_args.env_name).get(label)
    if group is None or conf_args.env_name is None:
        return default or ""
    if (override := os.environ.get(f"{_FACTOR_ENV_PREFIX}{label}")) is not None:
        return override
    env_factors = set(conf_args.env_name.split("-"))
    for value in group.values:
        if value in env_factors:
            return value
    return default if default is not None else group.default or ""


__all__ = [
    "MatchExpression",
    "MatchRecursionError",
    "RawText",
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
