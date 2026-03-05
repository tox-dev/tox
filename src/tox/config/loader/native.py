from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from tox.config.set_env import SetEnv
from tox.config.types import Command, EnvList
from tox.tox_env.python.pip.req_file import PythonDeps


def to_native(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float, str)):
        return value
    if isinstance(value, Path):
        return str(value)
    return _to_native_complex(value)


def _to_native_complex(value: Any) -> Any:
    if isinstance(value, SetEnv):
        return {k: to_native(value.load(k)) for k in sorted(value)}
    if isinstance(value, PythonDeps):
        return to_native(value.lines())
    if isinstance(value, EnvList):
        return value.envs
    if isinstance(value, Command):
        return value.shell
    return _to_native_collection(value)


def _to_native_collection(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): to_native(v) for k, v in value.items()}
    if isinstance(value, set):
        return sorted(str(i) for i in value)
    if isinstance(value, Sequence):
        return [to_native(i) for i in value]
    return str(value)


__all__ = ("to_native",)
