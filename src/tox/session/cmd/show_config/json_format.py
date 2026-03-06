from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from colorama import Fore

from .common import build_structured_result, write_output

if TYPE_CHECKING:
    from tox.session.state import State

_KEY_RE = re.compile(
    r"""
    ^ ([ ]*)        # leading indentation
    " ([^"]+) "     # quoted key name
    :               # colon separator
    """,
    re.MULTILINE | re.VERBOSE,
)


def show_config_json(state: State) -> int:
    result, has_exception = build_structured_result(state)
    output = json.dumps(result, indent=2)
    write_output(output, state.conf.options.output_file, state.conf.options.is_colored, colorize)
    return -1 if has_exception else 0


def colorize(text: str) -> str:
    return _KEY_RE.sub(rf"\1{Fore.GREEN}\2{Fore.RESET}:", text)
