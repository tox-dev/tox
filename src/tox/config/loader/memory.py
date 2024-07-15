from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator, Sequence

from tox.config.types import Command, EnvList

from .api import Loader, Override
from .section import Section
from .str_convert import StrConvert

if TYPE_CHECKING:
    from tox.config.main import Config


class MemoryLoader(Loader[Any]):
    def __init__(self, raw: dict[str, Any], *, section: Section | None = None, overrides: list[Override] | None = None,
                 ) -> None:
        section = section or Section(prefix="<memory>", name=str(id(self)))
        super().__init__(section, overrides or [])
        self.raw = raw

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(section={self._section.key}, overrides={self.overrides!r})"

    def load_raw(self, key: Any, conf: Config | None, env_name: str | None) -> Any:  # noqa: ARG002
        return self.raw[key]

    def found_keys(self) -> set[str]:
        return set(self.raw.keys())

    @staticmethod
    def to_bool(value: Any) -> bool:
        return bool(value)

    @staticmethod
    def to_str(value: Any) -> str:
        return str(value)

    @staticmethod
    def to_list(value: Any, of_type: type[Any]) -> Iterator[Any]:  # noqa: ARG004
        return iter(value)

    @staticmethod
    def to_set(value: Any, of_type: type[Any]) -> Iterator[Any]:  # noqa: ARG004
        return iter(value)

    @staticmethod
    def to_dict(value: Any, of_type: tuple[type[Any], type[Any]]) -> Iterator[tuple[Any, Any]]:  # noqa: ARG004
        return value.items()  # type: ignore[no-any-return]

    @staticmethod
    def to_path(value: Any) -> Path:
        return Path(value)

    @staticmethod
    def to_command(value: Any) -> Command:
        if isinstance(value, Command):
            return value
        if isinstance(value, str):
            return StrConvert.to_command(value)
        raise TypeError(value)

    @staticmethod
    def to_env_list(value: Any) -> EnvList:
        if isinstance(value, EnvList):
            return value
        if isinstance(value, str):
            return StrConvert.to_env_list(value)
        if isinstance(value, Sequence):
            return EnvList(value)
        raise TypeError(value)
