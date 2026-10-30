from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Final, Protocol

from tox.config.set_env import SetEnv
from tox.config.types import Command, EnvList
from tox.tox_env.python.pip.req_file import PythonConstraints, PythonDeps
from tox.util.typing_compat import override

from .replacer import Arguments, quote_args

if TYPE_CHECKING:
    from typing_extensions import TypeIs


def stringify_reference(value: _Stringifiable, *, constant: bool) -> str:
    as_str: Final[str] = stringify(value)[0]
    if _is_command_argument_value(value) and (not isinstance(value, str) or constant):
        return Arguments(as_str)
    return as_str


def stringify(value: _Stringifiable) -> tuple[str, bool]:  # ruff:ignore[too-many-return-statements]
    if isinstance(value, str):
        return value, False
    if isinstance(value, (Path, float, int, bool)):
        return str(value), False
    if isinstance(value, Mapping):
        return "\n".join(f"{stringify(k)[0]}={stringify(v)[0]}" for k, v in value.items()), True
    if isinstance(value, Sequence):
        return "\n".join(stringify(i)[0] for i in value), True
    if isinstance(value, set):
        return "\n".join(sorted(stringify(i)[0] for i in value)), True
    if isinstance(value, EnvList):
        return "\n".join(value.envs), True
    if isinstance(value, Command):
        return quote_args(value.args), True
    if isinstance(value, SetEnv):
        return stringify({key: value.load(key) for key in sorted(value)})
    if isinstance(value, (PythonDeps, PythonConstraints)):
        return stringify(value.lines())
    return str(value), False


def _is_command_argument_value(value: object) -> TypeIs[str | Path | Sequence[str | Path] | set[str | Path]]:
    return isinstance(value, (str, Path)) or (
        isinstance(value, (Sequence, set)) and all(isinstance(entry, (str, Path)) for entry in value)
    )


class _Stringifiable(Protocol):
    @override
    def __str__(self) -> str: ...


__all__ = [
    "stringify",
    "stringify_reference",
]
