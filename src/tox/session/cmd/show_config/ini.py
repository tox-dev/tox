from __future__ import annotations

import os
import sys
from pathlib import Path
from textwrap import indent
from typing import TYPE_CHECKING

from colorama import Fore

from tox.config.loader.stringify import stringify

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from tox.config.sets import ConfigSet
    from tox.session.state import State
    from tox.tox_env.api import ToxEnv


def show_config_ini(state: State) -> int:
    output_file = state.conf.options.output_file
    # color belongs to the terminal only - a file must hold plain text
    is_colored = state.conf.options.is_colored and output_file is None
    keys: list[str] = state.conf.options.list_keys_only
    # the terminal streams each line as its value materializes (evaluation can be slow); a file is written whole
    lines: list[str] = []
    emit: Callable[[str], None] = lines.append if output_file is not None else _write_line
    has_exception = False
    is_first = True

    def _emit_env(tox_env: ToxEnv) -> None:
        nonlocal has_exception, is_first
        if not is_first:
            emit("")
        is_first = False
        emit(_colored(f"[testenv:{tox_env.conf.name}]", Fore.YELLOW, enabled=is_colored))
        if not keys:
            emit(_key_value("type", type(tox_env).__name__, is_colored=is_colored))
        if _emit_conf(emit, tox_env.conf, keys, is_colored=is_colored):
            has_exception = True

    for name in state.envs.iter(package=True):
        _emit_env(state.envs[name])

    if state.conf.options.env.is_all or state.conf.options.show_core:
        emit("")
        emit(_colored("[tox]", Fore.YELLOW, enabled=is_colored))
        if _emit_conf(emit, state.conf.core, keys, is_colored=is_colored):
            has_exception = True
    if output_file is not None:
        Path(output_file).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return -1 if has_exception else 0


def _write_line(line: str) -> None:
    sys.stdout.write(line + "\n")


def _emit_conf(emit: Callable[[str], None], conf: ConfigSet, keys: Iterable[str], *, is_colored: bool) -> bool:
    has_exception = False
    for key in keys or conf:
        if key not in conf:
            continue
        key = conf.primary_key(key)  # ruff:ignore[redefined-loop-name]
        try:
            value = conf[key]
            as_str, multi_line = stringify(value)
        except Exception as exception:  # because e.g. the interpreter cannot be found
            if os.environ.get("_TOX_SHOW_CONFIG_RAISE"):  # pragma: no branch
                raise  # pragma: no cover
            as_str, multi_line = _colored(f"# Exception: {exception!r}", Fore.LIGHTRED_EX, enabled=is_colored), False
            has_exception = True
        if multi_line and "\n" not in as_str:
            multi_line = False
        emit(_key_value(key, as_str, is_colored=is_colored, multi_line=multi_line))
    unused = conf.unused()
    if unused and not keys:
        emit(_colored(f"# !!! unused: {', '.join(unused)}", Fore.CYAN, enabled=is_colored))
    return has_exception


def _key_value(key: str, value: str, *, is_colored: bool, multi_line: bool = False) -> str:
    if multi_line:
        return f"{_colored(key, Fore.GREEN, enabled=is_colored)} =\n{indent(value, prefix='  ')}"
    return f"{_colored(key, Fore.GREEN, enabled=is_colored)} = {value}"


def _colored(msg: str, color: int, *, enabled: bool) -> str:
    return f"{color}{msg}{Fore.RESET}" if enabled else msg


__all__ = [
    "show_config_ini",
]
