from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from tox.config.loader.native import to_native

if TYPE_CHECKING:
    from collections.abc import Callable

    from tox.config.sets import ConfigSet
    from tox.session.state import State


def build_structured_result(state: State) -> tuple[dict[str, Any], bool]:
    keys: list[str] = state.conf.options.list_keys_only
    show_everything = state.conf.options.env.is_all
    has_exception = False
    result: dict[str, Any] = {}

    envs: dict[str, Any] = {}
    for name in state.envs.iter(package=True):
        tox_env = state.envs[name]
        env_data, exc = _collect_conf(tox_env.conf, keys)
        if not keys:
            env_data = {"type": type(tox_env).__name__, **env_data}
        if exc:
            has_exception = True
        envs[tox_env.conf.name] = env_data
    result["env"] = envs

    if show_everything or state.conf.options.show_core:
        tox_data, exc = _collect_conf(state.conf.core, keys)
        has_exception = has_exception or exc
        result["tox"] = tox_data

    return result, has_exception


def write_output(
    output: str,
    output_file: Path | None,
    is_colored: bool,  # noqa: FBT001
    colorize: Callable[[str], str],
) -> None:
    if output_file is not None:
        Path(output_file).write_text(output + "\n", encoding="utf-8")
    else:
        print(colorize(output) if is_colored else output)  # noqa: T201


def _collect_conf(conf: ConfigSet, keys: list[str]) -> tuple[dict[str, Any], bool]:
    data: dict[str, Any] = {}
    has_exception = False
    for key in keys or conf:
        if key not in conf:
            continue
        key = conf.primary_key(key)  # noqa: PLW2901
        try:
            data[key] = to_native(conf[key])
        except Exception as exception:
            if os.environ.get("_TOX_SHOW_CONFIG_RAISE"):  # pragma: no branch
                raise  # pragma: no cover
            data[key] = {"error": repr(exception)}
            has_exception = True
    if (unused := conf.unused()) and not keys:
        data["unused"] = sorted(unused)
    return data, has_exception
