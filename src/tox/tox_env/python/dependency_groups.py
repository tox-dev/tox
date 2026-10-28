from __future__ import annotations

import tomllib
from collections import defaultdict
from typing import TYPE_CHECKING, TypedDict

from packaging.markers import Marker
from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

from tox.tox_env.errors import Fail

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Final

    from packaging.utils import NormalizedName


_IncludeGroup = TypedDict("_IncludeGroup", {"include-group": str})


def resolve(root: Path, groups: set[str]) -> set[Requirement]:
    pyproject_file = root / "pyproject.toml"
    if not pyproject_file.exists():
        msg = f"no pyproject.toml found at {pyproject_file} to read dependency groups from"
        raise Fail(msg)
    pyproject = tomllib.loads(pyproject_file.read_text(encoding="utf-8-sig"))
    if "dependency-groups" not in pyproject:
        msg = f"no dependency groups defined in {pyproject_file}"
        raise Fail(msg)
    dependency_groups_raw = pyproject["dependency-groups"]
    if not isinstance(dependency_groups_raw, dict):
        msg = f"dependency-groups is {type(dependency_groups_raw).__name__} instead of table"
        raise Fail(msg)
    original_names_lookup, dependency_groups = _normalize_group_names(dependency_groups_raw)
    result: set[Requirement] = set()
    for group in groups:
        result = result.union(_resolve_dependency_group(dependency_groups, group, original_names_lookup))

    project: Final = pyproject.get("project", {})
    if not (project_name := project.get("name")):
        return result
    optional_dependencies: Final[dict[str, list[str]]] = {
        canonicalize_name(name): deps for name, deps in project.get("optional-dependencies", {}).items()
    }

    return _unwrap_nested_extras(optional_dependencies, canonicalize_name(project_name), result)


def _normalize_group_names(
    dependency_groups: dict[str, list[str | _IncludeGroup]],
) -> tuple[dict[str, str], dict[str, list[str | _IncludeGroup]]]:
    original_names: defaultdict[str, list[str]] = defaultdict(list)
    normalized_groups: dict[str, list[str | _IncludeGroup]] = {}

    for group_name, value in dependency_groups.items():
        normed_group_name: str = canonicalize_name(group_name)
        original_names[normed_group_name].append(group_name)
        normalized_groups[normed_group_name] = value

    errors = []
    for normed_name, names in original_names.items():
        if len(names) > 1:
            errors.append(f"{normed_name} ({', '.join(names)})")
    if errors:
        msg = f"Duplicate dependency group names: {', '.join(errors)}"
        raise ValueError(msg)

    original_names_lookup = {
        normed_name: original_names[0]
        for normed_name, original_names in original_names.items()
        if len(original_names) == 1
    }

    return original_names_lookup, normalized_groups


def _resolve_dependency_group(
    dependency_groups: dict[str, list[str | _IncludeGroup]],
    group: str,
    original_names_lookup: dict[str, str],
    past_groups: tuple[str, ...] = (),
) -> set[Requirement]:
    if group in past_groups:
        original_group = original_names_lookup.get(group, group)
        original_past_groups = tuple(original_names_lookup.get(g, g) for g in past_groups)
        msg = f"Cyclic dependency group include: {original_group!r} -> {original_past_groups!r}"
        raise Fail(msg)
    if group not in dependency_groups:
        original_group = original_names_lookup.get(group, group)
        msg = f"dependency group {original_group!r} not found"
        raise Fail(msg)
    raw_group = dependency_groups[group]
    if not isinstance(raw_group, list):
        original_group = original_names_lookup.get(group, group)
        msg = f"dependency group {original_group!r} is not a list"
        raise Fail(msg)

    result = set()
    for item in raw_group:
        if isinstance(item, str):
            result.add(_parse_requirement(item))
        elif isinstance(item, dict) and tuple(item.keys()) == ("include-group",):
            include_group = canonicalize_name(str(next(iter(item.values()))))
            result = result.union(
                _resolve_dependency_group(
                    dependency_groups, include_group, original_names_lookup, (*past_groups, group)
                )
            )
        else:
            msg = f"invalid dependency group item: {item!r}"
            raise Fail(msg)
    return result


def _parse_requirement(requirement: str) -> Requirement:
    try:
        return Requirement(requirement)
    except InvalidRequirement as exc:
        msg = f"{requirement!r} is not valid requirement due to {exc}"
        raise Fail(msg) from exc


def _unwrap_nested_extras(
    optional_dependencies: dict[str, list[str]],
    project_name: NormalizedName,
    dependencies: set[Requirement],
) -> set[Requirement]:
    seen_extras: Final[set[tuple[str, frozenset[Marker]]]] = set()
    pending: Final[list[tuple[Requirement, frozenset[Marker]]]] = [(dep, frozenset()) for dep in dependencies]
    resolved: Final[set[Requirement]] = set()
    while pending:
        dependency, markers = pending.pop()
        if canonicalize_name(dependency.name) != project_name:
            if markers:  # the self-reference this came from only applies where its own marker does
                dependency.marker = Marker(
                    " and ".join(f"({marker})" for marker in (*sorted(markers, key=str), dependency.marker) if marker)
                )
            resolved.add(dependency)
            continue
        if dependency.marker is not None:
            markers |= {dependency.marker}
        for extra in dependency.extras:
            _add_extra_to_deps(optional_dependencies, pending, extra, markers, seen_extras)
    return resolved


def _add_extra_to_deps(
    optional_dependencies: dict[str, list[str]],
    pending: list[tuple[Requirement, frozenset[Marker]]],
    extra: str,
    markers: frozenset[Marker],
    seen_extras: set[tuple[str, frozenset[Marker]]],
) -> None:
    normalized_extra: Final = canonicalize_name(extra)
    if (normalized_extra, markers) in seen_extras:
        return
    seen_extras.add((normalized_extra, markers))
    if normalized_extra not in optional_dependencies:
        msg = f"extra {extra!r} not found in dependency groups"
        raise Fail(msg)
    pending.extend(
        (_parse_requirement(requirement), markers) for requirement in optional_dependencies[normalized_extra]
    )


__all__ = [
    "resolve",
]
