from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Set, Tuple, Type, cast

from tox.config.loader.convert import T
from tox.config.main import Config
from tox.config.types import Command, EnvList

from .api import Loader
from .section import Section
from .str_convert import StrConvert


class MemoryLoader(Loader[Any]):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(Section(prefix="<memory>", name=str(id(self))), [])
        self.raw: Dict[str, Any] = {**kwargs}

    def load_raw(self, key: Any, conf: Optional["Config"], env_name: Optional[str]) -> T:  # noqa: U100
        return cast(T, self.raw[key])

    def found_keys(self) -> Set[str]:
        return set(self.raw.keys())

    @staticmethod
    def to_bool(value: Any) -> bool:
        return bool(value)

    @staticmethod
    def to_str(value: Any) -> str:
        return str(value)

    @staticmethod
    def to_list(value: Any, of_type: Type[Any]) -> Iterator[T]:  # noqa: U100
        return iter(value)

    @staticmethod
    def to_set(value: Any, of_type: Type[Any]) -> Iterator[T]:  # noqa: U100
        return iter(value)

    @staticmethod
    def to_dict(value: Any, of_type: Tuple[Type[Any], Type[Any]]) -> Iterator[Tuple[T, T]]:  # noqa: U100
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
        raise TypeError(value)
