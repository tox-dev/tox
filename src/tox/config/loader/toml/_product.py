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
    expanded = [expand_factor_group(g) for g in raw_groups]
    exclude = set(value.get("exclude") or [])
    return [name for combo in product(*expanded) if (name := "-".join(combo)) not in exclude]


_RESERVED_LABELS: frozenset[str] = frozenset({"env", "posargs", "tty", "glob", "factor"})


def expand_factor_group(group: Any) -> list[str]:
    if isinstance(group, list):
        return [str(item) for item in group]
    if isinstance(group, dict):
        if "prefix" in group:
            return _expand_range(group)
        if len(group) == 1:
            label, values = next(iter(group.items()))
            if label in _RESERVED_LABELS:
                msg = f"'{label}' is reserved and cannot be used as a factor label"
                raise TypeError(msg)
            if not isinstance(values, list):
                msg = f"labeled factor group '{label}' must map to a list, got {type(values).__name__}"
                raise TypeError(msg)
            return [str(v) for v in values]
    msg = f"factor group must be a list, a range dict, or a labeled dict, got {type(group).__name__}"
    raise TypeError(msg)


def extract_label(group: Any) -> str | None:
    if isinstance(group, dict) and "prefix" not in group and len(group) == 1:
        return str(next(iter(group)))
    return None


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
    "_RESERVED_LABELS",
    "expand_factor_group",
    "expand_product",
    "extract_label",
]
