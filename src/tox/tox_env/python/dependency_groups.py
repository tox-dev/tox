from __future__ import annotations

import sys
from collections import defaultdict
from typing import TYPE_CHECKING, TypedDict

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

from tox.tox_env.errors import Fail

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Final

    from packaging.utils import NormalizedName


if sys.version_info >= (3, 11):  # pragma: >=3.11 cover
    import tomllib
else:  # pragma: <3.11 cover
    import tomli as tomllib

_IncludeGroup = TypedDict("_IncludeGroup", {"include-group": str})


def resolve(root: Path, groups: set[str]) -> set[Requirement]:
    pyproject_file = root / "pyproject.toml"
    if not pyproject_file.exists():  # check if it's static PEP-621 metadata
        return set()
    with pyproject_file.open("rb") as file_handler:
        pyproject = tomllib.load(file_handler)
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
    dependency_groups: dict[str, list[str] | _IncludeGroup],
) -> tuple[dict[str, str], dict[str, list[str] | _IncludeGroup]]:
    original_names = defaultdict(list)
    normalized_groups = {}

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
    dependency_groups: dict[str, list[str] | _IncludeGroup],
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
    seen_extras: Final[set[str]] = set()
    while extras_to_unwrap := {dep for dep in dependencies if canonicalize_name(dep.name) == project_name}:
        dependencies.difference_update(extras_to_unwrap)
        for dependency in extras_to_unwrap:
            for extra in dependency.extras:
                _add_extra_to_deps(optional_dependencies, dependencies, extra, seen_extras)
    return dependencies


def _add_extra_to_deps(
    optional_dependencies: dict[str, list[str]],
    dependencies: set[Requirement],
    extra: str,
    seen_extras: set[str],
) -> None:
    normalized_extra: Final = canonicalize_name(extra)
    if normalized_extra in seen_extras:
        return
    seen_extras.add(normalized_extra)
    if normalized_extra not in optional_dependencies:
        msg = f"extra {extra!r} not found in dependency groups"
        raise Fail(msg)
    dependencies.update(_parse_requirement(requirement) for requirement in optional_dependencies[normalized_extra])


__all__ = [
    "resolve",
]
