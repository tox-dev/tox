"""Load from a pyproject.toml file, native format."""

from __future__ import annotations

import sys
from itertools import product
from typing import TYPE_CHECKING, Any, Final, cast

from tox.config.loader.section import Section
from tox.config.loader.toml import TomlLoader
from tox.config.loader.toml._product import FactorGroup, expand_factor_group, extract_default, extract_label
from tox.config.types import MissingRequiredConfigKeyError
from tox.report import HandledError

from .api import Source

if sys.version_info >= (3, 11):  # pragma: >=3.11 cover
    import tomllib
else:  # pragma: <3.11 cover
    import tomli as tomllib

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from pathlib import Path

    from tox.config.loader.api import Loader, OverrideMap
    from tox.config.loader.toml._api import TomlTypes
    from tox.config.sets import CoreConfigSet


class TomlSection(Section):
    SEP: str = "."
    PREFIX: tuple[str, ...]
    ENV: Final[str] = "env"
    ENV_BASE: Final[str] = "env_base"
    RUN_ENV_BASE: Final[str] = "env_run_base"
    PKG_ENV_BASE: Final[str] = "env_pkg_base"

    @classmethod
    def test_env(cls, name: str) -> TomlSection:
        return cls(cls.env_prefix(), name)

    @classmethod
    def env_prefix(cls) -> str:
        return cls.SEP.join((*cls.PREFIX, cls.ENV))

    @classmethod
    def core_prefix(cls) -> str:
        return cls.SEP.join(cls.PREFIX)

    @classmethod
    def package_env_base(cls) -> str:
        return cls.SEP.join((*cls.PREFIX, cls.PKG_ENV_BASE))

    @classmethod
    def run_env_base(cls) -> str:
        return cls.SEP.join((*cls.PREFIX, cls.RUN_ENV_BASE))

    @classmethod
    def env_base_prefix(cls) -> str:
        return cls.SEP.join((*cls.PREFIX, cls.ENV_BASE))

    @classmethod
    def env_base(cls, name: str) -> TomlSection:
        return cls(cls.env_base_prefix(), name)

    @property
    def keys(self) -> Iterable[str]:
        # Build keys from prefix + name directly, preserving dots in names (e.g. env "py3.11").
        prefix, name = self._prefix, self._name
        if prefix is None and not name:
            return []
        parts: list[str] = prefix.split(self.SEP) if prefix else []
        if self.PREFIX and len(parts) >= len(self.PREFIX) and tuple(parts[: len(self.PREFIX)]) == self.PREFIX:
            parts = parts[len(self.PREFIX) :]  # strip global PREFIX (e.g. ("tool", "tox"))
        if name:
            parts.append(name)
        return parts


class TomlPyProjectSection(TomlSection):
    PREFIX = ("tool", "tox")


class TomlPyProject(Source):
    """Configuration sourced from a pyproject.toml files."""

    FILENAME = "pyproject.toml"
    _Section: type[TomlSection] = TomlPyProjectSection

    def __init__(self, path: Path) -> None:
        if path.name != self.FILENAME or not path.exists():
            raise ValueError
        with path.open("rb") as file_handler:
            self._content = tomllib.load(file_handler)
        try:
            self._our_content = _table_at(self._content, self._Section.PREFIX)
        except KeyError as exc:
            raise MissingRequiredConfigKeyError(path) from exc
        if set(self._our_content.keys()) <= {"legacy_tox_ini"}:  # an empty stub or a legacy pointer holds no config
            raise MissingRequiredConfigKeyError(path)
        env_base = self._our_content.get(self._Section.ENV_BASE, {})
        if not isinstance(env_base, dict):
            msg = f"{self._Section.ENV_BASE} must be a table"
            raise HandledError(msg)
        self._env_base_generated, self._factor_labels = _build_env_base_map(env_base)
        self._factor_labels.update(_extract_env_list_labels(self._our_content.get("env_list")))
        super().__init__(path)

    def get_core_section(self) -> Section:
        return self._Section(prefix=None, name="")

    def transform_section(self, section: Section) -> Section:
        return self._Section(section.prefix, section.name)

    def get_loader(self, section: Section, override_map: OverrideMap) -> Loader[Any] | None:
        current: TomlTypes = self._our_content
        sec = cast("TomlSection", section)
        for key in sec.keys:
            if not isinstance(current, dict) or key not in current:
                return None
            current = current[key]
        if not isinstance(current, dict):
            msg = f"{sec.key} must be a table, is {current.__class__.__name__!r}"
            raise HandledError(msg)
        is_core = section.prefix is None
        is_env_base = not is_core and sec.prefix == self._Section.env_base_prefix()
        unused_exclude: set[str] = set()
        if is_core:
            unused_exclude = {sec.ENV, sec.ENV_BASE, sec.RUN_ENV_BASE, sec.PKG_ENV_BASE}
        elif is_env_base:
            unused_exclude = {"factors"}
        return TomlLoader(
            section=section,
            overrides=override_map.get(section.key, []),
            content=current,
            root_content=self._content,
            unused_exclude=unused_exclude,
        )

    def envs(self, core_conf: CoreConfigSet) -> Iterator[str]:
        yield from core_conf["env_list"]
        yield from [section.name for section in self.sections()]
        yield from self._env_base_generated

    def sections(self) -> Iterator[Section]:
        # iterating a table gives its keys, but a list of names is tolerated too, hence the Iterable cast
        for env_name in cast("Iterable[object]", self._our_content.get(self._Section.ENV, {})):
            if not isinstance(env_name, str):
                msg = f"Environment key must be string, got {env_name!r}"
                raise HandledError(msg)
            yield self._Section.test_env(env_name)

    def get_base_sections(self, base: list[str], in_section: Section) -> Iterator[Section]:
        core_prefix = self._Section.core_prefix()
        strip = f"{core_prefix}{self._Section.SEP}" if core_prefix else ""
        env_base_pfx = self._Section.env_base_prefix()
        env_base_dot = f"{env_base_pfx}{self._Section.SEP}"
        for entry in base:
            if entry.startswith(env_base_dot):
                yield self._Section.env_base(entry[len(env_base_dot) :])
            else:
                yield self._Section(prefix=core_prefix or None, name=entry.removeprefix(strip))
                if in_section.prefix is not None:
                    yield self._Section(prefix=in_section.prefix, name=entry)

    def get_tox_env_section(self, item: str) -> tuple[Section, list[str], list[str]]:
        if base_name := self._env_base_generated.get(item):
            return (
                self._Section.test_env(item),
                [self._Section.env_base_prefix() + self._Section.SEP + base_name, self._Section.run_env_base()],
                [self._Section.package_env_base()],
            )
        return self._Section.test_env(item), [self._Section.run_env_base()], [self._Section.package_env_base()]


def _table_at(content: dict[str, TomlTypes], keys: tuple[str, ...]) -> dict[str, TomlTypes]:
    for key in keys:
        step = content[key]
        if not isinstance(step, dict):
            raise KeyError(key)  # a scalar where a table is required means the config is not for us
        content = step
    return content


def _build_env_base_map(env_base_content: dict[str, TomlTypes]) -> tuple[dict[str, str], dict[str, FactorGroup]]:
    result: dict[str, str] = {}
    all_labels: dict[str, FactorGroup] = {}
    for base_name, config in env_base_content.items():
        if not isinstance(config, dict):
            msg = f"env_base.{base_name} must be a table"
            raise HandledError(msg)
        factors_raw = config.get("factors")
        if factors_raw is None:
            msg = f"env_base.{base_name} requires a 'factors' key; use [env.{base_name}] for single environments"
            raise HandledError(msg)
        if not isinstance(factors_raw, list):
            msg = f"env_base.{base_name}.factors must be a list, got {type(factors_raw).__name__}"
            raise HandledError(msg)
        if factors_raw and isinstance(factors_raw[0], list | dict):
            expanded: list[list[str]] = []
            for idx, g in enumerate(factors_raw):
                values = expand_factor_group(g)
                expanded.append(values)
                group = FactorGroup(values=values, default=extract_default(g, values))
                all_labels[str(idx)] = group
                if (label := extract_label(g)) is not None:
                    all_labels[label] = group
            names = ["-".join(combo) for combo in product(*expanded)]
        else:
            names = [str(f) for f in factors_raw]
        for factor_suffix in names:
            result[f"{base_name}-{factor_suffix}"] = base_name
    return result, all_labels


def _extract_env_list_labels(env_list_raw: TomlTypes) -> dict[str, FactorGroup]:
    if not isinstance(env_list_raw, list):
        return {}
    labels: dict[str, FactorGroup] = {}
    for item in env_list_raw:
        if isinstance(item, dict) and "product" in item:
            raw_groups = item["product"]
            if not isinstance(raw_groups, list):
                continue
            for idx, g in enumerate(raw_groups):
                values = expand_factor_group(g)
                group = FactorGroup(values=values, default=extract_default(g, values))
                labels[str(idx)] = group
                if (label := extract_label(g)) is not None:
                    labels[label] = group
    return labels


__all__ = [
    "TomlPyProject",
]
