from __future__ import annotations

import ast
import glob
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, cast

from tox.config.loader.api import apply_overrides_to_raw
from tox.config.loader.ini.factor import active_factors
from tox.config.loader.replacer import (
    BACKSLASH_ESCAPE_CHARS,
    MatchError,
    MatchRecursionError,
    ReplaceReference,
    load_posargs,
    replace,
    replace_env,
)
from tox.config.loader.stringify import stringify
from tox.config.set_env import SetEnvReference
from tox.config.types import Command, EnvList
from tox.tox_env.python.pip.req_file import PythonConstraints, PythonDeps
from tox.util.typing_compat import override

from ._validate import validate

if TYPE_CHECKING:
    from collections.abc import Iterator

    from tox.config.loader.api import ConfigLoadArgs
    from tox.config.loader.toml import TomlLoader
    from tox.config.main import Config
    from tox.config.sets import ConfigSet
    from tox.config.source.toml_pyproject import TomlSection

    from ._api import TomlTypes


class _Directive(Protocol):
    def __call__(self, value: dict[str, TomlTypes], depth: int, /, *, skip_str: bool) -> TomlTypes: ...


class Unroll:
    def __init__(self, conf: Config | None, loader: TomlLoader, args: ConfigLoadArgs) -> None:
        self.conf = conf
        self.loader = loader
        self.args = args
        self._refs: list[str] = []
        self.factors = active_factors(args.env_name)

    def __call__(self, value: TomlTypes, depth: int = 0, *, skip_str: bool = False) -> TomlTypes:
        """Replace all active tokens within value according to the config."""
        depth += 1
        MatchRecursionError.check(depth, value)
        if isinstance(value, SetEnvReference):
            return value
        if isinstance(value, str):
            if not skip_str and self.conf is not None:  # core config does not support string substitution
                reference = TomlReplaceLoader(self.conf, self.loader)
                value = replace(self.conf, reference, value, self.args)
            return value
        if isinstance(value, list):
            return self._replace_list(value, depth, skip_str=skip_str)
        if isinstance(value, dict):
            return self._replace_dict(value, depth, skip_str=skip_str)
        return value  # int, float or bool: no reference or substitution possible

    def _replace_list(self, value: list[TomlTypes], depth: int, *, skip_str: bool) -> TomlTypes:
        # need to inspect every entry of the list to check for reference.
        res_list: list[TomlTypes] = []
        for val in value:  # apply replacement for every entry
            got = self(val, depth, skip_str=skip_str)
            if isinstance(got, SetEnvReference):
                extending = isinstance(val, dict) and bool(val.get("extend"))
                if got.shape != ("array" if extending else "table"):
                    msg = "set_env arrays require table references or array references with extend=true"
                    raise TypeError(msg)
                res_list.append(got)
            elif not (isinstance(val, dict) and val.get("replace") and val.get("extend")):
                res_list.append(got)
            elif isinstance(got, str):
                # ``extend`` spreads an iterable result (list, set of extras, ...) into the
                # parent. A scalar string is the exception: iterating it would split it
                # character by character, so a non-empty one is appended as a single item while
                # an empty one (a false ``if`` with no ``else``, yielding "") contributes nothing.
                if got:
                    res_list.append(cast("TomlTypes", got))
            else:
                res_list.extend(cast("list[Any]", got))
        return res_list

    def _replace_dict(self, value: dict[str, TomlTypes], depth: int, *, skip_str: bool) -> TomlTypes:
        replace_type = value.get("replace")
        if (directive := self._directive(replace_type)) is None:
            # need to inspect every entry of the table to check for reference.
            return {key: self(val, depth, skip_str=skip_str) for key, val in value.items()}
        marker = value.get("marker")
        result = directive(value, depth, skip_str=skip_str)
        return {"value": result, "marker": marker} if marker else result

    def _directive(self, replace_type: TomlTypes) -> _Directive | None:
        if replace_type == "posargs" and self.conf is not None:
            return self._replace_posargs
        if replace_type == "env":
            return self._replace_env
        if replace_type == "glob":
            return self._replace_glob
        if replace_type == "if":
            return self._replace_if
        if replace_type == "ref":
            return self._replace_ref
        return None

    def _replace_posargs(self, value: dict[str, TomlTypes], depth: int, *, skip_str: bool) -> TomlTypes:
        got_posargs = load_posargs(cast("Config", self.conf), self.args)
        if got_posargs is None:
            return [self(v, depth, skip_str=skip_str) for v in cast("list[str]", value.get("default", []))]
        if validate(value.get("substitute", False), bool):
            return [self(arg, depth, skip_str=skip_str) for arg in got_posargs]
        return [*got_posargs]

    def _replace_env(self, value: dict[str, TomlTypes], depth: int, *, skip_str: bool) -> TomlTypes:
        name = validate(value["name"], str)
        default = validate(self(value.get("default", ""), depth, skip_str=skip_str), str)
        if skip_str:
            return _env_expression(name, default)  # set_env resolves it when read, seeing the keys next to it
        # use a copy of the chain so this substitution's env references do not leak into
        # adjacent entries of the same value tree and spuriously trip the circular check (#2869)
        return replace_env(self.conf, [name, default], self.args.copy())

    def _replace_glob(self, value: dict[str, TomlTypes], _depth: int, *, skip_str: bool) -> TomlTypes:  # ruff:ignore[unused-method-argument]
        return _replace_glob_toml(self.conf, value)

    def _replace_if(self, value: dict[str, TomlTypes], depth: int, *, skip_str: bool) -> TomlTypes:
        return _replace_if_toml(value, self, depth, self.factors, skip_str=skip_str)

    def _replace_ref(self, value: dict[str, TomlTypes], depth: int, *, skip_str: bool = False) -> TomlTypes:
        if self.conf is not None and (env := value.get("env")) and (key := value.get("key")):
            # the referenced value arrives converted for its own key, return it in the raw shape a TOML key parses
            return self._to_raw(self.conf.get_env(cast("str", env))[cast("str", key)])
        if of := value.get("of"):
            validated_of = validate(of, list[str])
            if (path := self.loader.section.SEP.join(validated_of)) in self._refs:
                msg = f"circular reference {' -> '.join([*self._refs, path])}"
                raise MatchRecursionError(msg)
            loaded: TomlTypes = self.loader.load_raw_from_root(path)
            if self.conf is not None:
                *namespace_parts, ref_key = validated_of
                namespace = self.loader.section.SEP.join(namespace_parts)
                keys = {"set_env", "setenv"} if ref_key in {"set_env", "setenv"} else {ref_key}
                overrides = [entry for entry in self.conf.overrides.get(namespace, []) if entry.key in keys]
                if skip_str and ref_key in {"set_env", "setenv"} and overrides:
                    args = self.args.copy()
                    args.chain.append(path)
                    loaded = self.loader.set_env_reference(loaded, overrides, self.conf, args)
                else:
                    loaded = apply_overrides_to_raw(overrides, ref_key, loaded)
            self._refs.append(path)
            try:
                return self(loaded, depth, skip_str=skip_str)
            finally:
                self._refs.pop()
        return value

    @staticmethod
    def _to_raw(value: object) -> TomlTypes:
        if isinstance(value, (PythonDeps, PythonConstraints)):
            value = value.lines()
        elif isinstance(value, Command):
            value = value.raw_args
        elif isinstance(value, list) and all(isinstance(entry, Command) for entry in value):
            value = [entry.raw_args for entry in value]
        elif isinstance(value, Path):
            value = str(value)
        elif isinstance(value, EnvList):
            value = list(value.envs)
        elif isinstance(value, set):  # sort it like stringify does, so the order is stable
            value = sorted(value)
        return cast("TomlTypes", value)


def _env_expression(name: str, default: str) -> str:
    """Write an ``env`` table as the ``{env:NAME:DEFAULT}`` string that resolves to the same value."""
    escaped_name = "".join(f"\\{char}" if char in BACKSLASH_ESCAPE_CHARS else char for char in name)
    # the default keeps its substitutions, but a brace it does not pair would end the expression early
    parts: list[str] = []
    unclosed: list[int] = []
    pos = 0
    while pos < len(default):
        piece = default[pos : pos + 2] if default[pos] == "\\" else default[pos]
        pos += len(piece)
        if piece == "{":
            unclosed.append(len(parts))
        elif piece == "}" and unclosed:
            unclosed.pop()
        elif piece == "}":
            piece = "\\}"
        parts.append(piece)
    for index in unclosed:
        parts[index] = "\\{"
    return f"{{env:{escaped_name}:{''.join(parts)}}}"


def _replace_glob_toml(conf: Config | None, value: dict[str, Any]) -> list[TomlTypes] | str:
    pattern = validate(value.get("pattern"), str)
    if not pattern:
        msg = "No pattern was supplied in glob replacement"
        raise MatchError(msg)
    if conf is not None and not Path(pattern).is_absolute():
        pattern = str(conf.core["tox_root"] / pattern)
    extending = value.get("extend", False)
    if matches := sorted(glob.glob(pattern, recursive=True)):  # ruff:ignore[glob]
        extended: list[TomlTypes] = list(matches)
        return extended if extending else " ".join(matches)
    default = value.get("default")
    if default is None:
        return [] if extending else ""
    return validate(default, list) if extending else validate(default, str)


def _replace_if_toml(
    value: dict[str, Any], unroll: Unroll, depth: int, factors: set[str], *, skip_str: bool = False
) -> TomlTypes:
    condition = value.get("condition")
    if not condition or not isinstance(condition, str):
        msg = "No condition was supplied in if replacement"
        raise MatchError(msg)
    if "then" not in value:
        msg = "No 'then' value was supplied in if replacement"
        raise MatchError(msg)
    matched = _evaluate_condition(condition, factors, unroll.args.env_name)
    return unroll(value["then"] if matched else value.get("else", ""), depth, skip_str=skip_str)


def _evaluate_condition(expr: str, factors: set[str], env_name: str | None) -> bool:
    """Evaluate a condition expression supporting env.VAR, factor.NAME lookups, comparisons, and boolean logic."""
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        msg = f"Invalid condition expression: {expr}"
        raise MatchError(msg) from None
    return bool(_eval_condition_node(tree.body, expr, factors, env_name))


def _eval_condition_node(node: ast.expr, expr: str, factors: set[str], env_name: str | None) -> str | bool:
    if isinstance(node, ast.BoolOp):
        return _eval_bool_op(node, expr, factors, env_name)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not bool(_eval_condition_node(node.operand, expr, factors, env_name))
    if isinstance(node, ast.Compare):
        return _eval_compare(node, expr, factors, env_name)
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if (lookup_result := _try_lookup_or_name(node, factors, env_name)) is not None:
        return lookup_result
    msg = f"Unsupported expression in condition: {ast.dump(node)}"
    raise MatchError(msg)


def _eval_bool_op(node: ast.BoolOp, expr: str, factors: set[str], env_name: str | None) -> bool:
    if isinstance(node.op, ast.And):
        return all(bool(_eval_condition_node(v, expr, factors, env_name)) for v in node.values)
    return any(bool(_eval_condition_node(v, expr, factors, env_name)) for v in node.values)


def _eval_compare(node: ast.Compare, expr: str, factors: set[str], env_name: str | None) -> bool:
    if len(node.ops) != 1 or len(node.comparators) != 1:
        msg = f"Unsupported expression in condition: {ast.dump(node)}"
        raise MatchError(msg)
    left = _eval_condition_node(node.left, expr, factors, env_name)
    right = _eval_condition_node(node.comparators[0], expr, factors, env_name)
    if isinstance(node.ops[0], ast.Eq):
        return left == right
    if isinstance(node.ops[0], ast.NotEq):
        return left != right
    msg = f"Unsupported comparison operator in condition: {expr}"
    raise MatchError(msg)


def _try_lookup_or_name(node: ast.expr, factors: set[str], env_name: str | None) -> str | bool | None:
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return _lookup_namespace(node.value.id, node.attr, factors)
    if (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and isinstance(node.slice, ast.Constant)
        and isinstance(node.slice.value, str)
    ):
        return _lookup_namespace(node.value.id, node.slice.value, factors)
    if isinstance(node, ast.Name) and node.id == "env_name":
        return env_name or ""
    return None


def _lookup_namespace(namespace: str, key: str, factors: set[str]) -> str | bool:
    if namespace == "env":
        return os.environ.get(key, "")
    if namespace == "factor":
        return key in factors
    msg = f"Unsupported namespace in condition: {namespace} (expected 'env' or 'factor')"
    raise MatchError(msg)


_REFERENCE_PATTERN = re.compile(
    r"""
    (\[(?P<section>.*)])? # default value
    (?P<key>[-a-zA-Z0-9_]+) # key
    (:(?P<default>.*))? # default value
    $
""",
    re.VERBOSE,
)


class TomlReplaceLoader(ReplaceReference):
    def __init__(self, conf: Config, loader: TomlLoader) -> None:
        self.conf = conf
        self.loader = loader

    @override
    def __call__(self, value: str, conf_args: ConfigLoadArgs) -> str | None:
        if match := _REFERENCE_PATTERN.search(value):
            settings = match.groupdict()
            exception: Exception | None = None
            try:
                for src in self._config_value_sources(settings["section"], conf_args.env_name):
                    try:
                        value = src.load(settings["key"], conf_args.chain)
                    except KeyError as exc:  # if fails, keep trying maybe another source can satisfy
                        exception = exc
                    else:
                        return stringify(value)[0]
            except Exception as exc:  # ruff:ignore[blind-except]
                exception = exc
            if exception is not None:
                if isinstance(exception, KeyError):  # if the lookup failed replace - else keep
                    default = settings["default"]
                    if default is not None:
                        return default
                    return None  # keep original text, consistent with ini loader behavior
                raise exception
        return None  # not a reference, such as the {} of a format string

    def _config_value_sources(self, sec: str | None, current_env: str | None) -> Iterator[ConfigSet | RawLoader]:
        if sec is None:
            if current_env is not None:  # pragma: no branch
                yield self.conf.get_env(current_env)
            yield self.conf.core
            return

        section = cast("TomlSection", self.loader.section)
        core_prefix = section.core_prefix()
        env_prefix = section.env_prefix()
        run_env_base = section.run_env_base()
        pkg_env_base = section.package_env_base()
        if sec.startswith(env_prefix) and sec not in {run_env_base, pkg_env_base}:
            env = sec[len(env_prefix) + len(section.SEP) :]
            yield self.conf.get_env(env)
        else:
            yield RawLoader(self.loader, sec)
        if sec == core_prefix:
            yield self.conf.core  # try via registered configs


class RawLoader:
    def __init__(self, loader: TomlLoader, section: str) -> None:
        self._loader = loader
        self._section = section

    def load(self, item: str, chain: list[str] | None = None) -> Any:  # ruff:ignore[unused-method-argument]
        return self._loader.load_raw_from_root(f"{self._section}{self._loader.section.SEP}{item}")


__all__ = [
    "TomlReplaceLoader",
    "Unroll",
]
