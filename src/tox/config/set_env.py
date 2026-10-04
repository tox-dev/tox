from __future__ import annotations

import sys
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from packaging.markers import Marker

from tox.config.loader.api import ConfigLoadArgs
from tox.report import HandledError
from tox.tox_env.errors import Fail

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator, Mapping

if sys.version_info >= (3, 11):  # pragma: >=3.11 cover
    from typing import NotRequired, TypedDict
else:  # pragma: <3.11 cover
    from typing_extensions import NotRequired, TypedDict


class Replacer(Protocol):
    def __call__(self, value: str, args: ConfigLoadArgs, /, *, recursive: bool = ...) -> str: ...


class SetEnvEntry(TypedDict):
    """A single ``set_env`` value in structured (TOML) form."""

    value: str
    marker: NotRequired[str]


SetEnvRaw = str | dict[str, "str | SetEnvEntry"] | list[dict[str, "str | SetEnvEntry"]]


class SetEnv:
    def __init__(  # ruff:ignore[complex-structure, too-many-branches]
        self, raw: SetEnvRaw, name: str, env_name: str | None, root: Path, *, substituted: bool = False
    ) -> None:
        self.changed = False
        self._materialized: dict[str, str] = {}  # env vars we already loaded
        self._raw: dict[str, str] = {}  # could still need replacement
        self._exported: dict[str, Callable[[], str]] = {}  # tox's own values, read from settings on first use
        self._defined_keys: set[str] = set()  # keys explicitly defined during parsing (survives load() draining _raw)
        self._markers: dict[str, Marker] = {}  # PEP-496 markers for conditional env vars
        self._needs_replacement: list[str] = []  # env vars that need replacement
        self._expanding = False
        self._env_files: list[tuple[str, set[str]]] = []
        self._replacer: Replacer = lambda s, c, *, recursive=True: s  # ruff:ignore[unused-lambda-argument]
        self._name, self._env_name, self._root = name, env_name, root
        from .loader.replacer import MatchExpression, find_replace_expr  # ruff:ignore[import-outside-top-level]

        if isinstance(raw, dict):
            self._parse_dict(raw.items())
            return
        if isinstance(raw, list):
            # stream the entries in order rather than merging them into a dict first: a dict keeps only the last
            # ``file`` entry and pulls a repeated key back to its first position, both of which change the meaning
            self._parse_dict(chain.from_iterable(entry.items() for entry in raw))
            return
        keys_after_file: set[str] = set()
        for line in raw.splitlines():  # ruff:ignore[too-many-nested-blocks]
            if line.strip():
                if self._is_file_line(line):
                    self._env_files.append((self._parse_file_line(line), keys_after_file := set()))
                else:
                    try:
                        key, value, marker = self._extract_key_value_marker(line)
                        # in substituted text a brace that opens no expression is part of the key, as before
                        if "{" in key and (
                            not substituted
                            or any(isinstance(expr, MatchExpression) for expr in find_replace_expr(line))
                        ):
                            msg = f"invalid line {line!r} in set_env"
                            raise ValueError(msg)  # ruff:ignore[raise-within-try]
                    except ValueError:
                        for expr in find_replace_expr(line):
                            if isinstance(expr, MatchExpression):
                                self._needs_replacement.append(line)
                                break
                        else:
                            raise
                    else:
                        self._raw[key] = value
                        self._defined_keys.add(key)
                        keys_after_file.add(key)
                        if marker:
                            self._markers[key] = Marker(marker)
                        else:
                            self._markers.pop(key, None)

    def _parse_dict(self, raw: Iterable[tuple[str, str | SetEnvEntry]]) -> None:
        keys_after_file: set[str] = set()
        for key, value in raw:
            if not isinstance(value, str):
                if "value" in value:
                    self._raw[key] = value["value"]
                    self._defined_keys.add(key)
                    keys_after_file.add(key)
                    if marker := value.get("marker"):
                        self._markers[key] = Marker(marker)
                    else:  # an unconditional redefinition drops the marker an earlier entry set, as the INI form does
                        self._markers.pop(key, None)
            elif key == "file":
                self._env_files.append((value, keys_after_file := set()))
            else:
                self._raw[key] = value
                self._defined_keys.add(key)
                keys_after_file.add(key)
                self._markers.pop(key, None)

    @staticmethod
    def _is_file_line(line: str) -> bool:
        return line.startswith("file|")

    @staticmethod
    def _parse_file_line(line: str) -> str:
        return line[len("file|") :]

    def _marker_matches(self, key: str) -> bool:
        if key not in self._markers:
            return True
        return self._markers[key].evaluate()

    def use_replacer(self, value: Replacer, args: ConfigLoadArgs) -> None:
        self._replacer = value
        for filename, keys_after in self._env_files:
            for key, val in self._stream_env_file(filename, args):
                if key not in keys_after:
                    self._raw[key] = val
                    self._markers.pop(key, None)

    def _stream_env_file(self, filename: str, args: ConfigLoadArgs) -> Iterator[tuple[str, str]]:
        # Our rules in the documentation, some upstream environment file rules (we follow mostly the docker one):
        # - https://www.npmjs.com/package/dotenv#rules
        # - https://docs.docker.com/compose/env-file/
        env_file = Path(self._replacer(filename, args.copy()))  # apply any replace options
        env_file = env_file if env_file.is_absolute() else self._root / env_file
        if not env_file.exists():
            msg = f"{env_file} does not exist for set_env"
            raise Fail(msg)
        for env_line in env_file.read_text(encoding="utf-8").splitlines():
            env_line = env_line.strip()  # ruff:ignore[redefined-loop-name]
            if not env_line or env_line.startswith("#"):
                continue
            yield self._extract_key_value(env_line)

    @staticmethod
    def _extract_key_value(line: str) -> tuple[str, str]:
        """Split an environment file line; markers do not apply here, so ``;`` is a plain value character."""
        key, sep, value = line.partition("=")
        if not sep:
            msg = f"invalid line {line!r} in set_env"
            raise ValueError(msg)
        return key.strip(), value.strip()

    @staticmethod
    def _extract_key_value_marker(line: str) -> tuple[str, str, str]:
        key, sep, rest = line.partition("=")
        if not sep:
            msg = f"invalid line {line!r} in set_env"
            raise ValueError(msg)
        value, marker = SetEnv._split_value_marker(rest.strip())
        return key.strip(), value, marker

    @staticmethod
    def _split_value_marker(value: str) -> tuple[str, str]:
        # Parse value; marker format (PEP-496 style)
        # Handle escaped semicolons (\;) and quoted strings. Quotes keep a ";" inside a quoted value from being read
        # as the marker separator, but only when balanced -- a lone quote (e.g. an apostrophe in the value) must not
        # swallow the marker, so retry ignoring quotes if one is left open.
        for respect_quotes in (True, False):
            in_quotes = False
            quote_char = ""
            index = 0
            while index < len(value):
                char = value[index]
                if respect_quotes and char in {'"', "'"} and (index == 0 or value[index - 1] != "\\"):
                    if not in_quotes:
                        in_quotes, quote_char = True, char
                    elif char == quote_char:
                        in_quotes = False
                elif char == ";" and not in_quotes and (index == 0 or value[index - 1] != "\\"):
                    return value[:index].strip().replace("\\;", ";"), value[index + 1 :].strip()
                index += 1
            if not in_quotes:
                break  # quotes balanced or absent: the first pass is authoritative
        return value.replace("\\;", ";"), ""

    def load(self, item: str, args: ConfigLoadArgs | None = None) -> str:
        if item in self._materialized:
            return self._materialized[item]
        if item in self._exported:
            self._materialized[item] = self._exported.pop(item)()
            return self._materialized[item]
        raw = self._raw[item]
        args = ConfigLoadArgs([], self._name, self._env_name) if args is None else args
        if args.chain[-1:] != [f"env:{item}"]:  # an {env:...} lookup already recorded the key it resolves
            args.chain.append(f"env:{item}")
        result = self._replacer(raw, args)  # apply any replace options
        result = result.replace(r"\#", "#")  # unroll escaped comment with replacement
        self._materialized[item] = result
        self._raw.pop(item, None)  # if the replace requires the env we may be called again, so allow pop to fail
        return result

    def __contains__(self, item: object) -> bool:
        return isinstance(item, str) and item in iter(self)

    def __iter__(self) -> Iterator[str]:
        # start with the materialized ones, maybe we don't need to materialize the raw ones
        for key in self._materialized:
            if self._marker_matches(key):
                yield key
        yield from list(self._exported)
        for key in list(self._raw.keys()):  # iterating over this may trigger materialization and change the dict
            if self._marker_matches(key):
                yield key
        yield from self._iter_needs_replacement()

    def _iter_needs_replacement(self) -> Iterator[str]:
        if self._expanding:  # a lookup made while expanding sees only the keys registered so far
            return
        args = ConfigLoadArgs([], self._name, self._env_name)
        entries: dict[str, tuple[str, Marker | None]] = {}
        self._expanding = True
        try:
            for line in self._needs_replacement:
                entries.update(self._expand(line, (), args))
        finally:
            self._expanding = False
        self._needs_replacement.clear()
        sub_raw: dict[str, str] = {}
        for key, (value, marker) in entries.items():
            if key not in self._raw and key not in self._defined_keys and key not in self._exported:
                sub_raw[key] = value
                if marker is None:
                    self._markers.pop(key, None)
                else:
                    self._markers[key] = marker
        self._materialized = {k: v for k, v in self._materialized.items() if k not in sub_raw}
        self._raw.update(sub_raw)
        self.changed = True  # loading while iterating can cause these values to be missed
        for key in sub_raw:
            if self._marker_matches(key):
                yield key

    def _expand(
        self, line: str, parents: tuple[str, ...], args: ConfigLoadArgs
    ) -> dict[str, tuple[str, Marker | None]]:
        if line in parents:
            msg = f"circular set_env reference {' -> '.join((*parents, line))}"
            raise HandledError(msg)
        # paste the text as written and parse it like lines written in place, so its values resolve only when read
        if (text := self._replacer(line, args, recursive=False)) == line:  # nothing left to substitute, keep it as text
            key, value, marker = self._extract_key_value_marker(line)
            return {key: (value, Marker(marker) if marker else None)}
        block = SetEnv(text, self._name, self._env_name, self._root, substituted=True)
        block.use_replacer(self._replacer, args)
        entries: dict[str, tuple[str, Marker | None]] = {}
        for nested in block._needs_replacement:  # the block's own lines win over what it pulls in
            entries.update(self._expand(nested, (*parents, line), args))
        entries.update((key, (value, block._markers.get(key))) for key, value in block._raw.items())
        return entries

    def export(self, values: Mapping[str, Callable[[], str]]) -> None:
        """Set tox's own variables over the configured ones, resolved on first read.

        They come from settings that may read ``set_env`` through ``{env:...}``, so reading them here would recurse.

        """
        for key, value in values.items():
            self._raw.pop(key, None)
            self._materialized.pop(key, None)
            self._exported[key] = value
        self.changed = True

    def extend(self, other: SetEnv) -> None:
        """Take the lines of ``other`` as if written after these, so their values still expand only when read."""
        for key, value in other._raw.items():
            self._materialized.pop(key, None)
            self._raw[key] = value
            self._defined_keys.add(key)
            if key in other._markers:
                self._markers[key] = other._markers[key]
            else:
                self._markers.pop(key, None)
        self._needs_replacement.extend(other._needs_replacement)
        self.changed = True

    def update(self, param: Mapping[str, str] | SetEnv, *, override: bool = True) -> None:
        for key in param:
            # do not override something already set explicitly
            if override or (key not in self._raw and key not in self._materialized):
                value = param.load(key) if isinstance(param, SetEnv) else param[key]
                self._materialized[key] = value
                self.changed = True


__all__ = (
    "SetEnv",
    "SetEnvEntry",
    "SetEnvRaw",
)
