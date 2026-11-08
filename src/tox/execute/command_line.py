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
            if file_handler.read(2) != b"#!":
                return None
            shebang_line = file_handler.readline()
    except OSError:
        return None
    try:
        decoded = shebang_line.decode("UTF-8")
    except UnicodeDecodeError:
        return None
    # Match literal shebang paths while keeping tox's quoted path form.
    match: Final = re.fullmatch(
        r"""
        (?:
            " (?P<quoted> [^"]+ ) "    # a double-quoted path
            |
            (?P<bare> [^ \t]+ )        # an unquoted path up to the first whitespace
        )
        (?P<rest> .* )                 # the arguments that follow the path
        """,
        decoded.strip(),
        re.VERBOSE,
    )
    if match is None:
        return None
    try:
        return [match["quoted"] or match["bare"], *shlex.split(match["rest"], posix=True)]
    except ValueError:
        return None


def is_batch_file(exe: str) -> bool:
    # Windows ignores trailing dots and spaces in file names.
    """Check whether an executable is a Windows batch file.

    :param exe: the name of the executable

    :returns: whether the name ends with ``.bat`` or ``.cmd``

    """
    return exe.rstrip(". ").lower().endswith((".bat", ".cmd"))


def batch_file_command_line(script: str, args: Sequence[str]) -> str:
    """Build the command line that runs a batch file.

    :param script: the batch file
    :param args: the arguments of the batch file

    :returns: the command line

    :raises Fail: when the batch file name or an argument contains a character that cannot be quoted

    """
    if any(char in script for char in '"\r\n\0'):
        msg = f"cannot run batch file {script!r}, its name cannot be quoted"
        raise Fail(msg)
    if any(char in arg for arg in args for char in "\r\n\0"):
        msg = f"cannot pass an argument containing a line break or null character to batch file {script}"
        raise Fail(msg)
    line: Final[str] = " ".join([f'"{_escape_percent(script)}"', *(_quote_batch_file_arg(arg) for arg in args)])
    # Extensions enable the percent escape; delayed expansion must stay off to preserve !.
    return f'cmd.exe /e:ON /v:OFF /d /c "{line}"'


def _escape_percent(value: str) -> str:
    # The empty expansion prevents cmd from pairing the percent signs in a value.
    return value.replace("%", "%%cd:~,%")


def _quote_batch_file_arg(arg: str) -> str:
    # A trailing backslash can escape a quote added by the batch file.
    if re.fullmatch(r"[\w#$*+\-./:?@\\]*[\w#$*+\-./:?@]", arg):
        return arg
    escaped: Final[str] = re.sub(
        r"""
        (?<! \\ )                # the run starts after a character that is not a backslash
        (?P<slashes> \\* )       # backslashes that precede the quote
        (?P<quote> " | \Z )      # a double quote or the end of the argument
        """,
        lambda match: match["slashes"] * 2 + match["quote"] * 2,
        arg,
        flags=re.VERBOSE,
    )
    return f'"{_escape_percent(escaped)}"'


__all__ = [
    "batch_file_command_line",
    "is_batch_file",
    "shebang",
]
