from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Final

from colorama import Fore

from .common import build_structured_result, write_output

if TYPE_CHECKING:
    from tox.session.state import State

_KEY_RE: Final[re.Pattern[str]] = re.compile(
    r"""
    ^ (?P<indent>[ ]*)  # leading indentation
    " (?P<key>[^"]+) "  # quoted key name
    :               # colon separator
    """,
    re.MULTILINE | re.VERBOSE,
)


def show_config_json(state: State) -> int:
    """Show the configuration in the JSON format.

    :param state: the state of the run

    :returns: the exit code

    """
    result, has_exception = build_structured_result(state)
    write_output(json.dumps(result, indent=2), state.conf.options.output_file, state.conf.options.is_colored, colorize)
    return -1 if has_exception else 0


def colorize(text: str) -> str:
    """Add the color to the keys of a JSON output.

    :param text: the JSON text

    :returns: the colored text

    """  # simplint: ignore[function-docstring] existing formatter docs
    return _KEY_RE.sub(rf"\g<indent>{Fore.GREEN}\g<key>{Fore.RESET}:", text)


__all__ = [
    "show_config_json",
]
