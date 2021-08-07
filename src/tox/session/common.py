from argparse import ArgumentParser
from typing import Any, Iterator, List, Optional, Union

from tox.config.loader.str_convert import StrConvert


class CliEnv:
    def __init__(self, value: Union[None, List[str], str] = None):
        if isinstance(value, str):
            value = StrConvert().to(value, of_type=List[str], kwargs={})
        self._names = value

    def __iter__(self) -> Iterator[str]:
        if self._names is not None:  # pragma: no branch
            yield from self._names

    def __str__(self) -> str:
        if self.all:
            return "ALL"
        if self.use_default_list:
            return "<env_list>"
        return ",".join(self)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({'' if self.use_default_list else repr(str(self))})"

    def __eq__(self, other: Any) -> bool:
        return type(self) == type(other) and self._names == other._names

    def __ne__(self, other: Any) -> bool:
        return not (self == other)

    @property
    def all(self) -> bool:
        return "ALL" in self

    @property
    def use_default_list(self) -> bool:
        return len(list(self)) == 0


def env_list_flag(parser: ArgumentParser, default: Optional[CliEnv] = None, multiple: bool = True) -> None:
    help_msg = (
        "tox environment(s) to run (ALL -> all environments, not set -> <env_list>)"
        if multiple
        else "tox environment to run"
    )
    parser.add_argument("-e", dest="env", help=help_msg, default=CliEnv() if default is None else default, type=CliEnv)
