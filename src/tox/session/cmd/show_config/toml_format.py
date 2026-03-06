from __future__ import annotations

import re
from typing import TYPE_CHECKING

import tomli_w
from colorama import Fore

from .common import build_structured_result, write_output

if TYPE_CHECKING:
    from tox.session.state import State

_HEADER_RE = re.compile(
    r"""
    ^ \[ .* ] $     # section header like [env.py]
    """,
    re.MULTILINE | re.VERBOSE,
)
_KEY_RE = re.compile(
    r"""
    ^ ( [a-zA-Z_]       # key starts with letter or underscore
        [a-zA-Z0-9_-]*  # followed by alphanumerics, underscores, or hyphens
      )
    \s* =               # equals sign with optional whitespace
    """,
    re.MULTILINE | re.VERBOSE,
)


def show_config_toml(state: State) -> int:
    result, has_exception = build_structured_result(state)
    output = tomli_w.dumps(result).removesuffix("\n")
    write_output(output, state.conf.options.output_file, state.conf.options.is_colored, colorize)
    return -1 if has_exception else 0


def colorize(text: str) -> str:
    text = _HEADER_RE.sub(lambda m: f"{Fore.YELLOW}{m.group()}{Fore.RESET}", text)
    return _KEY_RE.sub(rf"{Fore.GREEN}\1{Fore.RESET} =", text)
