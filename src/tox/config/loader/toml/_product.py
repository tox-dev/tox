"""Expand TOML product dicts into environment name lists."""

from __future__ import annotations

from itertools import product
from typing import Any

from tox.config.loader.ini.factor import LATEST_PYTHON_MINOR_MAX, LATEST_PYTHON_MINOR_MIN


def expand_product(value: dict[str, Any]) -> list[str]:
    """Expand a product dict into a flat list of environment names.

    :param value: dict with ``product`` (list of factor groups) and optional ``exclude`` (list of env names to skip)

    :returns: list of environment names from the cartesian product of all factor groups, joined with ``-``

    """
    raw_groups = value["product"]
    if not isinstance(raw_groups, list):
        msg = f"product value must be a list of factor groups, got {type(raw_groups).__name__}"
        raise TypeError(msg)
    if not raw_groups:
        return []
    expanded = [_expand_factor_group(g) for g in raw_groups]
    exclude = set(value.get("exclude") or [])
    return [name for combo in product(*expanded) if (name := "-".join(combo)) not in exclude]


def _expand_factor_group(group: Any) -> list[str]:
    if isinstance(group, list):
        return [str(item) for item in group]
    if isinstance(group, dict) and "prefix" in group:
        return _expand_range(group)
    msg = f"factor group must be a list of strings or a range dict with 'prefix', got {type(group).__name__}"
    raise TypeError(msg)


def _expand_range(range_dict: dict[str, Any]) -> list[str]:
    prefix: str = str(range_dict["prefix"])
    has_start = "start" in range_dict
    has_stop = "stop" in range_dict
    if not has_start and not has_stop:
        msg = "range must have at least 'start' or 'stop'"
        raise TypeError(msg)
    start = range_dict.get("start", LATEST_PYTHON_MINOR_MIN)
    stop = range_dict.get("stop", LATEST_PYTHON_MINOR_MAX)
    if not isinstance(start, int):
        msg = f"range 'start' must be an integer, got {type(start).__name__}"
        raise TypeError(msg)
    if not isinstance(stop, int):
        msg = f"range 'stop' must be an integer, got {type(stop).__name__}"
        raise TypeError(msg)
    return [f"{prefix}{i}" for i in range(start, stop + 1)]


__all__ = [
    "expand_product",
]
