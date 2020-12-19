"""Convert string configuration values to tox python configuration objects."""
import os
import re
import shlex
from itertools import chain
from pathlib import Path
from typing import Any, Iterator, Tuple, Type

from tox.config.loader.convert import Convert
from tox.config.types import Command, EnvList


class StrConvert(Convert[str]):
    """A class converting string values to tox types"""

    @staticmethod
    def to_str(value: str) -> str:
        return str(value).strip()

    @staticmethod
    def to_path(value: str) -> Path:
        return Path(value)

    @staticmethod
    def to_list(value: str, of_type: Type[Any]) -> Iterator[str]:
        splitter = "\n" if issubclass(of_type, Command) or "\n" in value else ","
        splitter = splitter.replace("\r", "")
        for token in value.split(splitter):
            value = token.strip()
            if value:
                yield value

    @staticmethod
    def to_set(value: str, of_type: Type[Any]) -> Iterator[str]:
        for value in StrConvert.to_list(value, of_type):
            yield value

    @staticmethod
    def to_dict(value: str, of_type: Tuple[Type[Any], Type[Any]]) -> Iterator[Tuple[str, str]]:
        for row in value.split("\n"):
            row = row.strip()
            if row:
                try:
                    at = row.index("=")
                except ValueError:
                    raise TypeError(f"dictionary lines must be of form key=value, found {row}")
                else:
                    key = row[:at].strip()
                    value = row[at + 1 :].strip()
                    yield key, value

    @staticmethod
    def to_command(value: str) -> Command:
        posix = os.name != "nt"
        splitter = shlex.shlex(value, posix=posix)
        splitter.whitespace_split = True
        if posix:  # paths are expressed as POSIX - fix on non posix
            args = list(splitter)
        else:
            args = []
            for arg in splitter:
                if arg[0] == "'" and arg[-1] == "'":  # remove outer quote - the arg is passed as one, so no need for it
                    arg = arg[1:-1]
                if "/" in arg:  # normalize posix paths to nt paths
                    arg = "\\".join(re.split(pattern=r"[\\/]", string=arg))
                args.append(arg)
        return Command(args)

    @staticmethod
    def to_env_list(value: str) -> EnvList:
        from tox.config.loader.ini.factor import extend_factors

        elements = list(chain.from_iterable(extend_factors(expr) for expr in value.split("\n")))
        return EnvList(elements)

    TRUTHFUL_VALUES = {"true", "1", "yes", "on"}
    FALSE_VALUES = {"false", "0", "no", "off", ""}
    VALID_BOOL = list(sorted(TRUTHFUL_VALUES | FALSE_VALUES))

    @staticmethod
    def to_bool(value: str) -> bool:
        norm = value.strip().lower()
        if norm in StrConvert.TRUTHFUL_VALUES:
            return True
        elif norm in StrConvert.FALSE_VALUES:
            return False
        else:
            raise TypeError(f"value {value} cannot be transformed to bool, valid: {', '.join(StrConvert.VALID_BOOL)}")


__all__ = ("StrConvert",)
