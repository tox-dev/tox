from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from functools import reduce
from pathlib import Path
from typing import Any

from packaging.markers import Marker

from tox.config.loader.api import ConfigLoadArgs
from tox.tox_env.errors import Fail

Replacer = Callable[[str, ConfigLoadArgs], str]
SetEnvRaw = str | dict[str, Any] | list[dict[str, Any]]


class SetEnv:
    def __init__(  # noqa: C901, PLR0912
        self, raw: SetEnvRaw, name: str, env_name: str | None, root: Path
    ) -> None:
        self.changed = False
        self._materialized: dict[str, str] = {}  # env vars we already loaded
        self._raw: dict[str, str] = {}  # could still need replacement
        self._markers: dict[str, Marker] = {}  # PEP-496 markers for conditional env vars
        self._needs_replacement: list[str] = []  # env vars that need replacement
        self._env_files: list[str] = []
        self._replacer: Replacer = lambda s, c: s  # noqa: ARG005
        self._name, self._env_name, self._root = name, env_name, root
        from .loader.replacer import MatchExpression, find_replace_expr  # noqa: PLC0415

        if isinstance(raw, dict):
            self._parse_dict(raw)
            return
        if isinstance(raw, list):
            merged = reduce(lambda a, b: {**a, **b}, raw)
            self._parse_dict(merged)
            return
        for line in raw.splitlines():  # noqa: PLR1702
            if line.strip():
                if self._is_file_line(line):
                    self._env_files.append(self._parse_file_line(line))
                else:
                    try:
                        key, value, marker = self._extract_key_value_marker(line)
                        if "{" in key:
                            msg = f"invalid line {line!r} in set_env"
                            raise ValueError(msg)  # noqa: TRY301
                    except ValueError:
                        for expr in find_replace_expr(line):
                            if isinstance(expr, MatchExpression):
                                self._needs_replacement.append(line)
                                break
                        else:
                            raise
                    else:
                        self._raw[key] = value
                        if marker:
                            self._markers[key] = Marker(marker)

    def _parse_dict(self, raw: dict[str, Any]) -> None:
        for key, value in raw.items():
            if key == "file":
                self._env_files.append(value)
            elif isinstance(value, dict):
                if "value" in value:
                    self._raw[key] = value["value"]
                    if marker := value.get("marker"):
                        self._markers[key] = Marker(marker)
            else:
                self._raw[key] = value

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
        for filename in self._env_files:
            self._raw.update(self._stream_env_file(filename, args))

    def _stream_env_file(self, filename: str, args: ConfigLoadArgs) -> Iterator[tuple[str, str]]:
        # Our rules in the documentation, some upstream environment file rules (we follow mostly the docker one):
        # - https://www.npmjs.com/package/dotenv#rules
        # - https://docs.docker.com/compose/env-file/
        env_file = Path(self._replacer(filename, args.copy()))  # apply any replace options
        env_file = env_file if env_file.is_absolute() else self._root / env_file
        if not env_file.exists():
            msg = f"{env_file} does not exist for set_env"
            raise Fail(msg)
        for env_line in env_file.read_text().splitlines():
            env_line = env_line.strip()  # noqa: PLW2901
            if not env_line or env_line.startswith("#"):
                continue
            key, value, _ = self._extract_key_value_marker(env_line)
            yield key, value

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
        # Handle escaped semicolons (\;) and quoted strings
        in_quotes = False
        quote_char = ""
        i = 0
        while i < len(value):
            char = value[i]
            if char in {'"', "'"} and (i == 0 or value[i - 1] != "\\"):
                if not in_quotes:
                    in_quotes, quote_char = True, char
                elif char == quote_char:
                    in_quotes = False
            elif char == ";" and not in_quotes and (i == 0 or value[i - 1] != "\\"):
                return value[:i].strip(), value[i + 1 :].strip()
            i += 1
        return value, ""

    def load(self, item: str, args: ConfigLoadArgs | None = None) -> str:
        if item in self._materialized:
            return self._materialized[item]
        raw = self._raw[item]
        args = ConfigLoadArgs([], self._name, self._env_name) if args is None else args
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
        for key in list(self._raw.keys()):  # iterating over this may trigger materialization and change the dict
            if self._marker_matches(key):
                yield key
        yield from self._iter_needs_replacement()

    def _iter_needs_replacement(self) -> Iterator[str]:
        args = ConfigLoadArgs([], self._name, self._env_name)
        while self._needs_replacement:
            line = self._needs_replacement.pop(0)
            expanded_line = self._replacer(line, args)
            sub_raw: dict[str, str] = {}
            for sub_line in filter(None, expanded_line.splitlines()):
                if self._is_file_line(sub_line):
                    for key, value in self._stream_env_file(self._parse_file_line(sub_line), args):
                        if key not in self._raw:
                            sub_raw[key] = value  # noqa: PERF403
                else:
                    key, value, marker = self._extract_key_value_marker(sub_line)
                    sub_raw[key] = value
                    if marker:
                        self._markers[key] = Marker(marker)
            self._raw.update(sub_raw)
            self.changed = True  # loading while iterating can cause these values to be missed
            for key in sub_raw:
                if self._marker_matches(key):
                    yield key

    def update(self, param: Mapping[str, str] | SetEnv, *, override: bool = True) -> None:
        for key in param:
            # do not override something already set explicitly
            if override or (key not in self._raw and key not in self._materialized):
                value = param.load(key) if isinstance(param, SetEnv) else param[key]
                self._materialized[key] = value
                self.changed = True


__all__ = ("SetEnv",)
