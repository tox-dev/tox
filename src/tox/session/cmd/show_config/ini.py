from __future__ import annotations

import os
from textwrap import indent
from typing import TYPE_CHECKING

from colorama import Fore

from tox.config.loader.stringify import stringify

if TYPE_CHECKING:
    from collections.abc import Iterable

    from tox.config.sets import ConfigSet
    from tox.session.state import State
    from tox.tox_env.api import ToxEnv


def show_config_ini(state: State) -> int:
    is_colored = state.conf.options.is_colored
    keys: list[str] = state.conf.options.list_keys_only
    is_first = True
    has_exception = False

    def _print_env(tox_env: ToxEnv) -> None:
        nonlocal is_first, has_exception
        if is_first:
            is_first = False
        else:
            print()  # noqa: T201
        _print_section_header(is_colored, f"[testenv:{tox_env.conf.name}]")
        if not keys:
            _print_key_value(is_colored, "type", type(tox_env).__name__)
        if _print_conf(is_colored, tox_env.conf, keys):
            has_exception = True

    show_everything = state.conf.options.env.is_all
    done: set[str] = set()
    for name in state.envs.iter(package=True):
        done.add(name)
        _print_env(state.envs[name])

    if show_everything or state.conf.options.show_core:
        print()  # noqa: T201
        _print_section_header(is_colored, "[tox]")
        if _print_conf(is_colored, state.conf.core, keys):
            has_exception = True
    return -1 if has_exception else 0


def _colored(is_colored: bool, color: int, msg: str) -> str:  # noqa: FBT001
    return f"{color}{msg}{Fore.RESET}" if is_colored else msg


def _print_section_header(is_colored: bool, name: str) -> None:  # noqa: FBT001
    print(_colored(is_colored, Fore.YELLOW, name))  # noqa: T201


def _print_comment(is_colored: bool, comment: str) -> None:  # noqa: FBT001
    print(_colored(is_colored, Fore.CYAN, comment))  # noqa: T201


def _print_key_value(is_colored: bool, key: str, value: str, multi_line: bool = False) -> None:  # noqa: FBT001, FBT002
    print(_colored(is_colored, Fore.GREEN, key), end="")  # noqa: T201
    print(" =", end="")  # noqa: T201
    if multi_line:
        print()  # noqa: T201
        value_str = indent(value, prefix="  ")
    else:
        print(" ", end="")  # noqa: T201
        value_str = value
    print(value_str)  # noqa: T201


def _print_conf(is_colored: bool, conf: ConfigSet, keys: Iterable[str]) -> bool:  # noqa: FBT001
    has_exception = False
    for key in keys or conf:
        if key not in conf:
            continue
        key = conf.primary_key(key)  # noqa: PLW2901
        try:
            value = conf[key]
            as_str, multi_line = stringify(value)
        except Exception as exception:  # because e.g. the interpreter cannot be found
            if os.environ.get("_TOX_SHOW_CONFIG_RAISE"):  # pragma: no branch
                raise  # pragma: no cover
            as_str, multi_line = _colored(is_colored, Fore.LIGHTRED_EX, f"# Exception: {exception!r}"), False
            has_exception = True
        if multi_line and "\n" not in as_str:
            multi_line = False
        _print_key_value(is_colored, key, as_str, multi_line=multi_line)
    unused = conf.unused()
    if unused and not keys:
        _print_comment(is_colored, f"# !!! unused: {', '.join(unused)}")
    return has_exception
