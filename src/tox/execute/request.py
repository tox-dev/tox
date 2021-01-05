"""Module declaring a command execution request."""
import sys
from enum import Enum
from pathlib import Path
from typing import Dict, List, Sequence, Union


class StdinSource(Enum):
    OFF = 0
    USER = 1
    API = 2

    @staticmethod
    def user_only() -> "StdinSource":
        return StdinSource.USER if sys.stdin.isatty() else StdinSource.OFF


class ExecuteRequest:
    """Defines a commands execution request"""

    def __init__(
        self, cmd: Sequence[Union[str, Path]], cwd: Path, env: Dict[str, str], stdin: StdinSource, run_id: str
    ) -> None:
        if len(cmd) == 0:
            raise ValueError("cannot execute an empty command")
        self.cmd: List[str] = [str(i) for i in cmd]
        self.cwd = cwd
        self.env = env
        self.stdin = stdin
        self.run_id = run_id

    @property
    def shell_cmd(self) -> str:
        try:
            exe = str(Path(self.cmd[0]).relative_to(self.cwd))
        except ValueError:
            exe = self.cmd[0]
        _cmd = [exe]
        _cmd.extend(self.cmd[1:])
        return shell_cmd(_cmd)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(cmd={self.cmd!r}, cwd={self.cwd!r}, env=..., stdin={self.stdin!r})"


def shell_cmd(cmd: Sequence[str]) -> str:
    if sys.platform == "win32":  # pragma: win32 cover
        from subprocess import list2cmdline

        return list2cmdline(tuple(str(x) for x in cmd))
    else:  # pragma: win32 no cover
        from shlex import quote as shlex_quote

        return " ".join(shlex_quote(str(x)) for x in cmd)


__all__ = (
    "StdinSource",
    "ExecuteRequest",
    "shell_cmd",
)
