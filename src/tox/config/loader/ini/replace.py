"""Apply value substitution (replacement) on tox strings."""

from __future__ import annotations

import re
from configparser import SectionProxy
from functools import cache
from re import Pattern
from typing import TYPE_CHECKING, Final

from tox.config.loader.api import apply_overrides_to_raw
from tox.config.loader.replacer import ReplaceReference
from tox.config.loader.stringify import stringify
from tox.util.typing_compat import override

if TYPE_CHECKING:
    from collections.abc import Iterator

    from tox.config.loader.api import ConfigLoadArgs
    from tox.config.loader.ini import IniLoader
    from tox.config.main import Config
    from tox.config.sets import ConfigSet


class ReplaceReferenceIni(ReplaceReference):
    def __init__(self, conf: Config, loader: IniLoader) -> None:
        self.conf = conf
        self.loader = loader

    @override
    def __call__(self, value: str, conf_args: ConfigLoadArgs) -> str | None:
        # a return value of None indicates could not replace
        pattern = _replace_ref(self.loader.section.prefix or self.loader.section.name)
        match = pattern.match(value)
        if match:
            settings = match.groupdict()

            key = settings["key"]
            if settings["section"] is None and settings["full_env"]:
                settings["section"] = settings["full_env"]

            try:
                return self._load_from_sources(settings, key, conf_args)
            except KeyError:  # if the lookup failed replace - else keep
                # we cannot raise here as that would mean users could not write factorials:
                #   depends = {py39,py38}-{,b}
                return settings["default"]
        return None

    def _load_from_sources(self, settings: dict[str, str | None], key: str, conf_args: ConfigLoadArgs) -> str:
        for src in self._config_value_sources(settings["env"], settings["section"], conf_args.env_name):
            try:
                if isinstance(src, SectionProxy):
                    return self._resolve_section_proxy(src, key, conf_args)
                value = src.load(key, conf_args.chain)
            except KeyError:  # if fails, keep trying maybe another source can satisfy
                pass
            else:
                as_str, _ = stringify(value)
                return as_str.replace("#", r"\#")  # escape comment characters as these will be stripped
        raise KeyError(key)

    def _resolve_section_proxy(self, src: SectionProxy, key: str, args: ConfigLoadArgs) -> str:
        """Resolve a key from a SectionProxy, returning empty string when factor filtering empties the value."""
        keys = {"set_env", "setenv"} if key in {"set_env", "setenv"} else {key}
        overrides = [entry for entry in self.conf.overrides.get(src.name, []) if entry.key in keys]
        set_env_override = key in {"set_env", "setenv"} and bool(overrides)
        raw = src[key] if set_env_override else apply_overrides_to_raw(overrides, key, src[key])
        try:
            processed = self.loader.process_raw(self.conf, args.env_name, raw)
        except KeyError:
            # Factor filtering can empty an existing section value.
            processed = ""
        if not set_env_override:
            return processed
        args = args.copy()
        args.chain.append(f"{src.name}.{key}")
        escaped_semicolon: Final[str] = r"\;"
        values = self.loader.set_env_reference(processed, overrides, self.conf, args).config.raw(args)
        return "\n".join(
            f"{name}={value['value'].replace(';', escaped_semicolon)}"
            + (f"; {marker}" if (marker := value.get("marker")) else "")
            for name, value in values.items()
        )

    def _config_value_sources(
        self, env: str | None, section: str | None, current_env: str | None
    ) -> Iterator[SectionProxy | ConfigSet]:
        if section is None:
            if env is not None and env in self.conf:
                yield self.conf.get_env(env)
            # if no section specified perhaps it's an unregistered config:
            # 1. try first from core conf
            yield self.conf.core
            # 2. and then fallback to our own environment
            if current_env is not None:
                yield self.conf.get_env(current_env)
            return

        # if there's a section, special handle the core section
        if section == self.loader.core_section.name:
            yield self.conf.core  # try via registered configs
        # prefer raw section values so substitutions resolve in the calling env's context
        if (proxy := self.loader.get_section(section)) is not None:
            yield proxy
        # fallback to the env's ConfigSet for registered-only keys
        if env is not None and env in self.conf:
            yield self.conf.get_env(env)


@cache
def _replace_ref(env: str | None) -> Pattern[str]:
    return re.compile(
        rf"""
    (\[(?P<full_env>{re.escape(env or ".*")}(:(?P<env>[^]]+))?|(?P<section>[-\w]+))])? # env/section
    (?P<key>[-a-zA-Z0-9_]+) # key
    (:(?P<default>.*))? # default value
    $
""",
        re.VERBOSE,
    )


__all__ = [
    "ReplaceReferenceIni",
]
