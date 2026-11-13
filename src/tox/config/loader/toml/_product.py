"""Expand TOML product dicts into environment name lists."""

from __future__ import annotations

from itertools import product
from typing import TYPE_CHECKING

from tox.config.loader.ini.factor import open_minor_range

if TYPE_CHECKING:
    from ._api import TomlTypes


def expand_product(value: dict[str, TomlTypes]) -> list[str]:
    """Expand a product table into environment names.

    :param value: table with ``product`` factor groups and optional ``exclude`` names

    :returns: names from the Cartesian product of the groups, joined with ``-``

    :raises TypeError: when a group or exclusion has an unsupported shape

    """  # simplint: ignore[function-docstring] existing public helper
    raw_groups = value["product"]
    if not isinstance(raw_groups, list):
        msg = f"product value must be a list of factor groups, got {type(raw_groups).__name__}"
        raise TypeError(msg)
    if not raw_groups:
        return []
    expanded = [expand_factor_group(g) for g in raw_groups]
    exclude_raw = value.get("exclude") or []
    if not isinstance(exclude_raw, list):
        msg = f"product exclude must be a list, got {type(exclude_raw).__name__}"
        raise TypeError(msg)
    exclude = set(exclude_raw)
    return [name for combo in product(*expanded) if (name := "-".join(combo)) not in exclude]


def expand_factor_group(group: TomlTypes) -> list[str]:
    """Expand a list, range, or labeled factor group.

    :param group: the factor group

    :returns: the factor names

    :raises TypeError: when the group has an unsupported shape

    """  # simplint: ignore[function-docstring] existing public helper
    if isinstance(group, list):
        result: list[str] = []
        for item in group:
            if not isinstance(item, str):
                hint = (
                    " — pass range or labeled dicts directly as sibling factor groups, not nested inside a list"
                    if isinstance(item, dict)
                    else ""
                )
                msg = f"factor group list items must be strings, got {type(item).__name__}{hint}"
                raise TypeError(msg)
            result.append(item)
        return result
    if isinstance(group, dict):
        if "prefix" in group:
            return _expand_range(group)
        if len(group) == 1:
            return _expand_labeled(*next(iter(group.items())))
    msg = f"factor group must be a list, a range dict, or a labeled dict, got {type(group).__name__}"
    raise TypeError(msg)


def _expand_range(range_dict: dict[str, TomlTypes]) -> list[str]:
    prefix: str = str(range_dict["prefix"])
    start = range_dict.get("start")
    stop = range_dict.get("stop")
    if start is None and stop is None:
        msg = "range must have at least 'start' or 'stop'"
        raise TypeError(msg)
    if start is not None and type(start) is not int:  # bool subclasses int, so isinstance accepts true/false
        msg = f"range 'start' must be an integer, got {type(start).__name__}"
        raise TypeError(msg)
    if stop is not None and type(stop) is not int:
        msg = f"range 'stop' must be an integer, got {type(stop).__name__}"
        raise TypeError(msg)
    minors = open_minor_range(start, stop) if start is None or stop is None else range(start, stop + 1)
    return [f"{prefix}{i}" for i in minors]


def _expand_labeled(label: str, values: TomlTypes) -> list[str]:
    reserved_labels: frozenset[str] = frozenset({"env", "posargs", "tty", "glob", "factor"})
    if label in reserved_labels:
        msg = f"'{label}' is reserved and cannot be used as a factor label"
        raise TypeError(msg)
    if isinstance(values, dict):
        if "prefix" in values:
            return _expand_range(values)
        if (listed := values.get("values")) is not None:
            if not isinstance(listed, list):
                msg = f"labeled factor group '{label}' 'values' must be a list, got {type(listed).__name__}"
                raise TypeError(msg)
            return [str(v) for v in listed]
        msg = f"labeled factor group '{label}' maps to a dict with neither a 'prefix' nor a 'values' key"
        raise TypeError(msg)
    if not isinstance(values, list):
        msg = f"labeled factor group '{label}' must map to a list, a range dict, or a values dict, "
        msg += f"got {type(values).__name__}"
        raise TypeError(msg)
    return [str(v) for v in values]


def extract_default(group: TomlTypes, values: list[str]) -> str | None:
    """Read a factor group's default, if one is set.

    :param group: the factor group
    :param values: valid factors in the group

    :returns: the default factor or ``None``

    :raises TypeError: when the default is invalid

    """  # simplint: ignore[function-docstring] existing public helper
    if not isinstance(group, dict):
        return None
    table = group if "prefix" in group else next(iter(group.values()), None)
    if not isinstance(table, dict) or (default := table.get("default")) is None:
        return None
    if not isinstance(default, str):
        msg = f"factor group 'default' must be a string, got {type(default).__name__}"
        raise TypeError(msg)
    if default not in values:
        msg = f"factor group 'default' {default!r} is not one of its factors: {', '.join(values)}"
        raise TypeError(msg)
    return default


def extract_label(group: TomlTypes) -> str | None:
    """Read the label of a labeled factor group.

    :param group: the factor group

    :returns: the label or ``None``

    """  # simplint: ignore[function-docstring] existing public helper
    if isinstance(group, dict) and "prefix" not in group and len(group) == 1:
        return str(next(iter(group)))
    return None


__all__ = [
    "expand_factor_group",  # simplint: ignore[unused-export] existing public helper
    "expand_product",  # simplint: ignore[unused-export] existing public helper
    "extract_default",  # simplint: ignore[unused-export] existing public helper
    "extract_label",  # simplint: ignore[unused-export] existing public helper
]
