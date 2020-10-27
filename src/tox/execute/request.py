"""Module declaring a command execution request."""
import sys
from pathlib import Path
from typing import Dict, List, Sequence, Union


class ExecuteRequest:
    """Defines a commands execution request"""

    def __init__(self, cmd: Sequence[Union[str, Path]], cwd: Path, env: Dict[str, str], allow_stdin: bool):
        if len(cmd) == 0:
            raise ValueError("cannot execute an empty command")
        self.cmd: List[str] = [str(i) for i in cmd]
        self.cwd = cwd
        self.env = env
        self.allow_stdin = allow_stdin

    @property
    def shell_cmd(self) -> str:
        try:
            exe = str(Path(self.cmd[0]).relative_to(self.cwd))
        except ValueError:
            exe = self.cmd[0]
        _cmd = [exe]
        _cmd.extend(self.cmd[1:])
        return shell_cmd(_cmd)


def shell_cmd(cmd: Sequence[str]) -> str:
    if sys.platform.startswith("win"):
        from subprocess import list2cmdline

        return list2cmdline(tuple(str(x) for x in cmd))
    else:
        from shlex import quote as shlex_quote

        return " ".join(shlex_quote(str(x)) for x in cmd)


__all__ = (
    "ExecuteRequest",
    "shell_cmd",
)
