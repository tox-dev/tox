from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Final


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
    # Match literal shebang paths while keeping tox's quoted path form.
    match: Final = re.fullmatch(r'(?:"([^"]+)"|([^ \t]+))(.*)', decoded.strip())
    if match is None:
        return None
    try:
        return [match[1] or match[2], *shlex.split(match[3], posix=True)]
    except ValueError:
        return None


__all__ = [
    "shebang",
]
