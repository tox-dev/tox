from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from tox.config.types import Command, EnvList
from tox.util.typing_compat import override

from .api import Loader
from .section import Section
from .str_convert import StrConvert

if TYPE_CHECKING:
    from collections.abc import Iterator

    from tox.config.main import Config


class MemoryLoader(Loader[object]):
    """Loads configuration directly from data in memory.

    :param kwargs: the configuration values, keyed by name

    :var raw: the configuration values as set in memory

    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(Section(prefix="<memory>", name=str(id(self))), [])
        self.raw: dict[str, Any] = {  # simplint: ignore[imprecise-annotation]  # callers store any value in memory
            **kwargs
        }

    @override
    def load_raw(
        self, key: str, conf: Config | None, env_name: str | None
    ) -> object:  # simplint: ignore[imprecise-annotation]  # callers store any value in memory
        return self.raw[key]

    @override
    def found_keys(self) -> set[str]:
        return set(self.raw.keys())

    @staticmethod
    @override
    def to_bool(value: Any) -> bool:  # simplint: ignore[imprecise-annotation]  # callers store any value in memory
        return bool(value)

    @staticmethod
    @override
    def to_str(value: Any) -> str:  # simplint: ignore[imprecise-annotation]  # callers store any value in memory
        return str(value)

    @staticmethod
    @override
    def to_list(
        value: Any,  # simplint: ignore[imprecise-annotation]  # callers store any value in memory
        of_type: type[Any],  # simplint: ignore[imprecise-annotation]  # callers store any value in memory
    ) -> Iterator[Any]:  # simplint: ignore[imprecise-annotation]  # callers store any value in memory
        return iter(value)

    @staticmethod
    @override
    def to_set(
        value: Any,  # simplint: ignore[imprecise-annotation]  # callers store any value in memory
        of_type: type[Any],  # simplint: ignore[imprecise-annotation]  # callers store any value in memory
    ) -> Iterator[Any]:  # simplint: ignore[imprecise-annotation]  # callers store any value in memory
        return iter(value)

    @staticmethod
    @override
    def to_dict(
        value: Any,  # simplint: ignore[imprecise-annotation]  # callers store any value in memory
        of_type: tuple[
            type[Any], type[Any]  # simplint: ignore[imprecise-annotation]  # callers store any value in memory
        ],
    ) -> Iterator[tuple[Any, Any]]:  # simplint: ignore[imprecise-annotation]  # callers store any value in memory
        return iter(value.items())

    @staticmethod
    @override
    def to_path(value: Any) -> Path:  # simplint: ignore[imprecise-annotation]  # callers store any value in memory
        return Path(value)

    @staticmethod
    @override
    def to_command(
        value: Any,  # simplint: ignore[imprecise-annotation]  # callers store any value in memory
    ) -> Command:
        if isinstance(value, Command):
            return value
        if isinstance(value, str):
            return StrConvert.to_command(value)
        msg = f"command expected Command or str, got {type(value).__name__}: {value!r}"
        raise TypeError(msg)

    @staticmethod
    @override
    def to_env_list(
        value: Any,  # simplint: ignore[imprecise-annotation]  # callers store any value in memory
    ) -> EnvList:
        if isinstance(value, EnvList):
            return value
        if isinstance(value, str):
            return StrConvert.to_env_list(value)
        msg = f"env_list expected EnvList or str, got {type(value).__name__}: {value!r}"
        raise TypeError(msg)


__all__ = [
    "MemoryLoader",
]
