from collections import OrderedDict
from typing import Any, Iterator, List, Sequence

from tox.execute.request import shell_cmd


class Command:
    def __init__(self, args: List[str]) -> None:
        self.ignore_exit_code = args[0] == "-"
        self.args = args[1:] if self.ignore_exit_code else args

    def __repr__(self) -> str:
        return f"{type(self).__name__}(args={(['-'] if self.ignore_exit_code else [])+ self.args!r})"

    def __eq__(self, other: Any) -> bool:
        return type(self) == type(other) and (self.args, self.ignore_exit_code) == (other.args, other.ignore_exit_code)

    def __ne__(self, other: Any) -> bool:
        return not (self == other)

    @property
    def shell(self) -> str:
        return shell_cmd(self.args)


class EnvList:
    def __init__(self, envs: Sequence[str]) -> None:
        self.envs = list(OrderedDict((e, None) for e in envs).keys())

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.envs!r})"

    def __eq__(self, other: Any) -> bool:
        return type(self) == type(other) and self.envs == other.envs

    def __ne__(self, other: Any) -> bool:
        return not (self == other)

    def __iter__(self) -> Iterator[str]:
        return iter(self.envs)

    def __bool__(self) -> bool:
        return bool(self.envs)


__all__ = (
    "Command",
    "EnvList",
)
