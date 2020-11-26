from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Set, Tuple, Type, cast

from tox.config.loader.convert import T
from tox.config.main import Config
from tox.config.types import Command, EnvList

from .api import Loader


class MemoryLoader(Loader[Any]):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__([])
        self.raw: Dict[str, Any] = {**kwargs}

    def load_raw(self, key: Any, conf: Optional["Config"], env_name: Optional[str]) -> T:
        return cast(T, self.raw[key])

    def found_keys(self) -> Set[str]:
        return set(self.raw.keys())

    @staticmethod
    def to_bool(value: Any) -> bool:
        return value  # type: ignore[no-any-return]

    @staticmethod
    def to_str(value: Any) -> str:
        return value  # type: ignore[no-any-return]

    @staticmethod
    def to_list(value: Any, of_type: Type[Any]) -> Iterator[T]:
        return value  # type: ignore[no-any-return]

    @staticmethod
    def to_set(value: Any, of_type: Type[Any]) -> Iterator[T]:
        return iter(value)  # type: ignore[no-any-return]

    @staticmethod
    def to_dict(value: Any, of_type: Tuple[Type[Any], Type[Any]]) -> Iterator[Tuple[T, T]]:
        return value.items()  # type: ignore[no-any-return]

    @staticmethod
    def to_path(value: Any) -> Path:
        return value  # type: ignore[no-any-return]

    @staticmethod
    def to_command(value: Any) -> Command:
        return value  # type: ignore[no-any-return]

    @staticmethod
    def to_env_list(value: Any) -> EnvList:
        return value  # type: ignore[no-any-return]
