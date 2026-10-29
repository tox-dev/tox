from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import TYPE_CHECKING, Final

from tox.tox_env.errors import Fail

if TYPE_CHECKING:
    from collections.abc import Sequence


def shebang(exe: str) -> list[str] | None:
    """:param exe: the executable

    :returns: the shebang interpreter arguments

    """
    # When invoking a command using a shebang line that exceeds the OS shebang limit (e.g. Linux has a limit of 128;
    # BINPRM_BUF_SIZE) the invocation will fail. In this case you'd want to replace the shebang invocation with an
    # explicit invocation.
    # see https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/tree/fs/binfmt_script.c#n34
    try:
        with Path(exe).open("rb") as file_handler:
            marker = file_handler.read(2)
            if marker != b"#!":
                return None
            shebang_line = file_handler.readline()
    except OSError:
        return None
    try:
        decoded = shebang_line.decode("UTF-8")
    except UnicodeDecodeError:
        return None
    try:
        parts = shlex.split(decoded.strip(), posix=True)
    except ValueError:
        return None
    return parts or None


def is_batch_file(exe: str) -> bool:
    # Windows ignores trailing dots and spaces in file names.
    return exe.rstrip(". ").lower().endswith((".bat", ".cmd"))


def batch_file_command_line(script: str, args: Sequence[str]) -> str:
    if any(char in script for char in '"\r\n\0'):
        msg = f"cannot run batch file {script!r}, its name cannot be quoted"
        raise Fail(msg)
    if any(char in arg for arg in args for char in "\r\n\0"):
        msg = f"cannot pass an argument containing a line break or null character to batch file {script}"
        raise Fail(msg)
    line: Final[str] = " ".join([f'"{_escape_percent(script)}"', *(_quote_batch_file_arg(arg) for arg in args)])
    # Extensions enable the percent escape; delayed expansion must stay off to preserve !.
    return f'cmd.exe /e:ON /v:OFF /d /c "{line}"'


def _quote_batch_file_arg(arg: str) -> str:
    # A trailing backslash can escape a quote added by the batch file.
    if re.fullmatch(r"[\w#$*+\-./:?@\\]*[\w#$*+\-./:?@]", arg):
        return arg
    escaped: Final[str] = re.sub(r'(?<!\\)(\\*)("|\Z)', lambda match: match[1] * 2 + match[2] * 2, arg)
    return f'"{_escape_percent(escaped)}"'


def _escape_percent(value: str) -> str:
    # The empty expansion prevents cmd from pairing the percent signs in a value.
    return value.replace("%", "%%cd:~,%")


__all__ = [
    "batch_file_command_line",
    "is_batch_file",
    "shebang",
]
