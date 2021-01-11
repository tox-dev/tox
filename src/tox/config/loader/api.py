from abc import abstractmethod
from argparse import ArgumentTypeError
from concurrent.futures import Future
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Generator, List, Mapping, Optional, Set, Type, TypeVar

from tox.plugin.impl import impl

from .convert import Convert
from .str_convert import StrConvert

if TYPE_CHECKING:
    from tox.config.cli.parser import ToxParser
    from tox.config.main import Config


class Override:
    def __init__(self, value: str) -> None:
        split_at = value.find("=")
        if split_at == -1:
            raise ArgumentTypeError(f"override {value} has no = sign in it")
        key = value[:split_at]
        ns_at = key.find(".")
        self.namespace = "" if ns_at == -1 else key[:ns_at]
        self.key = key[ns_at + 1 :]
        self.value = value[split_at + 1 :]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self}')"

    def __str__(self) -> str:
        return f"{self.namespace}{'.' if self.namespace else ''}{self.key}={self.value}"

    def __eq__(self, other: Any) -> bool:
        if type(self) != type(other):
            return False
        return (self.namespace, self.key, self.value) == (other.namespace, other.key, other.value)

    def __ne__(self, other: Any) -> bool:
        return not (self == other)


OverrideMap = Mapping[str, List[Override]]

T = TypeVar("T")
V = TypeVar("V")


class Loader(Convert[T]):
    """Loader loads a configuration value and converts it."""

    def __init__(self, overrides: List[Override]) -> None:
        self.overrides = {o.key: o for o in overrides}

    @abstractmethod
    def load_raw(self, key: str, conf: Optional["Config"], env_name: Optional[str]) -> T:
        """
        Load the raw object from the config store.

        :param key: the key under what we want the configuration
        :param env_name: the name of the environment this load is happening for
        :param conf: the global config object
        """
        raise NotImplementedError

    @abstractmethod
    def found_keys(self) -> Set[str]:
        """A list of configuration keys found within the configuration."""
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"{type(self).__name__}"

    def load(
        self, key: str, of_type: Type[V], conf: Optional["Config"], env_name: Optional[str], chain: List[str]
    ) -> V:
        """
        Load a value.

        :param key: the key under it lives
        :param of_type: the type to convert to
        :param conf: the configuration object of this tox session (needed to manifest the value)
        :param env_name: env name
        :return: the converted type
        """
        if key in self.overrides:
            return _STR_CONVERT.to(self.overrides[key].value, of_type)
        raw = self.load_raw(key, conf, env_name)
        future: "Future[V]" = Future()
        with self.build(future, key, of_type, conf, env_name, raw, chain) as prepared:
            converted = self.to(prepared, of_type)
            future.set_result(converted)
        return converted

    @contextmanager
    def build(
        self,
        future: "Future[V]",
        key: str,
        of_type: Type[V],
        conf: Optional["Config"],
        env_name: Optional[str],
        raw: T,
        chain: List[str],
    ) -> Generator[T, None, None]:
        yield raw


@impl
def tox_add_option(parser: "ToxParser") -> None:
    parser.add_argument(
        "-x",
        "--override",
        action="append",
        type=Override,
        default=[],
        dest="override",
        help="configuration override(s)",
    )


_STR_CONVERT = StrConvert()
