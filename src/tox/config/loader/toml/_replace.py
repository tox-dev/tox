from __future__ import annotations

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from tox.config.loader.api import ConfigLoadArgs
    from tox.config.loader.toml import TomlLoader
    from tox.config.main import Config

    from ._api import TomlTypes

MAX_REPLACE_DEPTH: Final[int] = 100


class MatchRecursionError(ValueError):
    """Could not stabilize on replacement value."""


def unroll_refs_and_apply_substitutions(
    conf: Config | None,
    loader: TomlLoader,
    value: TomlTypes,
    args: ConfigLoadArgs,
    depth: int = 0,
) -> TomlTypes:
    """Replace all active tokens within value according to the config."""
    if depth > MAX_REPLACE_DEPTH:
        msg = f"Could not expand {value} after recursing {depth} frames"
        raise MatchRecursionError(msg)

    if isinstance(value, str):
        pass  # apply string substitution here
    elif isinstance(value, (int, float, bool)):
        pass  # no reference or substitution possible
    elif isinstance(value, list):
        # need to inspect every entry of the list to check for reference.
        res_list: list[TomlTypes] = []
        for val in value:  # apply replacement for every entry
            got = unroll_refs_and_apply_substitutions(conf, loader, val, args, depth + 1)
            res_list.append(got)
        value = res_list
    elif isinstance(value, dict):
        # need to inspect every entry of the list to check for reference.
        res_dict: dict[str, TomlTypes] = {}
        for key, val in value.items():  # apply replacement for every entry
            got = unroll_refs_and_apply_substitutions(conf, loader, val, args, depth + 1)
            res_dict[key] = got
        value = res_dict
    return value


__all__ = [
    "unroll_refs_and_apply_substitutions",
]
