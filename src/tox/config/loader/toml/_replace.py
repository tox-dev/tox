from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, cast

from tox.config.loader.replacer import MatchRecursionError, ReplaceReference, load_posargs, replace, replace_env
from tox.config.loader.stringify import stringify

from ._validate import validate

if TYPE_CHECKING:
    from collections.abc import Iterator

    from tox.config.loader.api import ConfigLoadArgs
    from tox.config.loader.toml import TomlLoader
    from tox.config.main import Config
    from tox.config.sets import ConfigSet
    from tox.config.source.toml_pyproject import TomlSection

    from ._api import TomlTypes


class Unroll:
    def __init__(self, conf: Config | None, loader: TomlLoader, args: ConfigLoadArgs) -> None:
        self.conf = conf
        self.loader = loader
        self.args = args

    def __call__(  # noqa: C901, PLR0912
        self, value: TomlTypes, depth: int = 0, *, skip_str: bool = False
    ) -> TomlTypes:
        """Replace all active tokens within value according to the config."""
        depth += 1
        MatchRecursionError.check(depth, value)
        if isinstance(value, str):
            if not skip_str and self.conf is not None:  # core config does not support string substitution
                reference = TomlReplaceLoader(self.conf, self.loader)
                value = replace(self.conf, reference, value, self.args)
        elif isinstance(value, (int, float, bool)):
            pass  # no reference or substitution possible
        elif isinstance(value, list):
            # need to inspect every entry of the list to check for reference.
            res_list: list[TomlTypes] = []
            for val in value:  # apply replacement for every entry
                got = self(val, depth, skip_str=skip_str)
                if isinstance(val, dict) and val.get("replace") and val.get("extend"):
                    res_list.extend(cast("list[Any]", got))
                else:
                    res_list.append(got)
            value = res_list
        elif isinstance(value, dict):
            # need to inspect every entry of the list to check for reference.
            if replace_type := value.get("replace"):
                marker = value.get("marker")
                if replace_type == "posargs" and self.conf is not None:
                    got_posargs = load_posargs(self.conf, self.args)
                    posargs_result: TomlTypes = (
                        [self(v, depth, skip_str=skip_str) for v in cast("list[str]", value.get("default", []))]
                        if got_posargs is None
                        else list(got_posargs)
                    )
                    return {"value": posargs_result, "marker": marker} if marker else posargs_result
                if replace_type == "env":
                    env_result: TomlTypes = replace_env(
                        self.conf,
                        [
                            validate(value["name"], str),
                            validate(self(value.get("default", ""), depth, skip_str=skip_str), str),
                        ],
                        self.args,
                    )
                    return {"value": env_result, "marker": marker} if marker else env_result
                if replace_type == "ref":  # pragma: no branch
                    ref_result = self._replace_ref(value, depth, skip_str=skip_str)
                    return {"value": ref_result, "marker": marker} if marker else ref_result

            res_dict: dict[str, TomlTypes] = {}
            for key, val in value.items():  # apply replacement for every entry
                res_dict[key] = self(val, depth, skip_str=skip_str)
            value = res_dict
        return value

    def _replace_ref(self, value: dict[str, TomlTypes], depth: int, *, skip_str: bool = False) -> TomlTypes:
        if self.conf is not None and (env := value.get("env")) and (key := value.get("key")):
            return cast("TomlTypes", self.conf.get_env(cast("str", env))[cast("str", key)])
        if of := value.get("of"):
            validated_of = validate(of, list[str])
            loaded = self.loader.load_raw_from_root(self.loader.section.SEP.join(validated_of))
            return self(loaded, depth, skip_str=skip_str)
        return value


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

    def __call__(self, value: str, conf_args: ConfigLoadArgs) -> str | None:
        if match := _REFERENCE_PATTERN.search(value):
            settings = match.groupdict()
            exception: Exception | None = None
            try:
                for src in self._config_value_sources(settings["section"], conf_args.env_name):
                    try:
                        value = src.load(settings["key"], conf_args.chain)
                    except KeyError as exc:  # if fails, keep trying maybe another source can satisfy # noqa: PERF203
                        exception = exc
                    else:
                        return stringify(value)[0]
            except Exception as exc:  # noqa: BLE001
                exception = exc
            if exception is not None:
                if isinstance(exception, KeyError):  # if the lookup failed replace - else keep
                    default = settings["default"]
                    if default is not None:
                        return default
                    return None  # keep original text, consistent with ini loader behavior
                raise exception
        return value

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

    def load(self, item: str, chain: list[str] | None = None) -> Any:  # noqa: ARG002
        return self._loader.load_raw_from_root(f"{self._section}{self._loader.section.SEP}{item}")


__all__ = [
    "TomlReplaceLoader",
    "Unroll",
]
