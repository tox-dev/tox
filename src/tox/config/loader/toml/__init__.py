from __future__ import annotations

import inspect
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar, cast

from tox.config.loader.api import ConfigLoadArgs, Loader, Override
from tox.config.loader.replacer import replace
from tox.config.set_env import SetEnv
from tox.config.types import Command, EnvList
from tox.report import HandledError

from ._api import TomlTypes
from ._replace import TomlReplaceLoader, Unroll
from ._validate import validate

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping
    from types import UnionType

    from tox.config.loader.convert import Factory
    from tox.config.loader.section import Section
    from tox.config.main import Config

_T = TypeVar("_T")
_V = TypeVar("_V")


class TomlLoader(Loader[TomlTypes]):
    """Load configuration from a pyproject.toml file."""

    def __init__(
        self,
        section: Section,
        overrides: list[Override],
        content: Mapping[str, TomlTypes],
        root_content: Mapping[str, TomlTypes],
        unused_exclude: set[str],
    ) -> None:
        self.content = content
        self._root_content = root_content
        self._unused_exclude = unused_exclude
        super().__init__(section, overrides)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.section.name}, {self.content!r})"

    def load_raw(self, key: str, conf: Config | None, env_name: str | None) -> TomlTypes:  # noqa: ARG002
        return self.content[key]

    def load_raw_from_root(self, path: str) -> TomlTypes:
        current = cast("TomlTypes", self._root_content)
        for key in path.split(self.section.SEP):
            if isinstance(current, dict):
                current = current[key]
            else:
                msg = f"Failed to load key {key} as not dictionary {current!r}"
                logging.warning(msg)
                raise KeyError(msg)
        return current

    def build(  # noqa: PLR0913
        self,
        key: str,  # noqa: ARG002
        of_type: type[_T] | UnionType,
        factory: Factory[_T],
        conf: Config | None,
        raw: TomlTypes,
        args: ConfigLoadArgs,
    ) -> _T:
        delay_replace = inspect.isclass(of_type) and issubclass(of_type, SetEnv)
        unroll = Unroll(conf=conf, loader=self, args=args)
        exploded = unroll(raw, skip_str=True) if delay_replace else unroll(raw)
        result = self.to(exploded, of_type, factory)
        if delay_replace:
            loader = self

            def _toml_replacer(value: str, args_: ConfigLoadArgs) -> str:
                if conf is None:
                    return value
                return replace(conf, TomlReplaceLoader(conf, loader), value, args_)

            result.use_replacer(_toml_replacer, args=args)
        return result

    def found_keys(self) -> set[str]:
        return set(self.content.keys()) - self._unused_exclude

    @staticmethod
    def to_str(value: TomlTypes) -> str:
        return validate(value, str)

    @staticmethod
    def to_bool(value: TomlTypes) -> bool:
        return validate(value, bool)

    @staticmethod
    def to_list(value: TomlTypes, of_type: type[_T]) -> Iterator[_T]:
        result = validate(value, cast("type[list[Any]]", list[of_type]))  # ty: ignore[invalid-type-form] # runtime generic from type variable
        return iter(cast("list[_T]", result))

    @staticmethod
    def to_set(value: TomlTypes, of_type: type[_T]) -> Iterator[_T]:
        result = validate(value, cast("type[list[Any]]", list[of_type]))  # ty: ignore[invalid-type-form] # runtime generic from type variable
        return iter(cast("list[_T]", result))

    @staticmethod
    def to_dict(value: TomlTypes, of_type: tuple[type[_T], type[_V]]) -> Iterator[tuple[_T, _V]]:
        result = validate(value, cast("type[dict[Any, Any]]", dict[of_type[0], of_type[1]]))  # ty: ignore[invalid-type-form] # runtime generic from type variables
        return iter(cast("dict[_T, _V]", result).items())

    @staticmethod
    def to_path(value: TomlTypes) -> Path:
        return Path(TomlLoader.to_str(value))

    @staticmethod
    def to_command(value: TomlTypes) -> Command | None:
        if value:
            return Command(args=cast("list[str]", value))  # validated during load in _ensure_type_correct
        return None

    @staticmethod
    def to_env_list(value: TomlTypes) -> EnvList:
        return EnvList(envs=list(TomlLoader.to_list(value, str)))


__all__ = [
    "HandledError",
    "TomlLoader",
]
