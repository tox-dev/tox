from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from packaging.requirements import Requirement

from .virtual_env.package.util import dependencies_with_extras_from_markers

if TYPE_CHECKING:
    from pathlib import Path

if sys.version_info >= (3, 11):  # pragma: no cover (py311+)
    import tomllib
else:  # pragma: no cover (py311+)
    import tomli as tomllib


def resolve_extras_static(root: Path, extras: set[str]) -> list[Requirement] | None:
    pyproject_file = root / "pyproject.toml"
    if not pyproject_file.exists():
        return None
    with pyproject_file.open("rb") as file_handler:
        pyproject = tomllib.load(file_handler)
    if "project" not in pyproject:
        return None
    project = pyproject["project"]
    for dynamic in project.get("dynamic", []):
        if dynamic == "dependencies" or (extras and dynamic == "optional-dependencies"):
            return None
    deps_with_markers: list[tuple[Requirement, set[str | None]]] = [
        (Requirement(i), {None}) for i in project.get("dependencies", [])
    ]
    optional_deps = project.get("optional-dependencies", {})
    for extra, reqs in optional_deps.items():
        deps_with_markers.extend((Requirement(req), {extra}) for req in (reqs or []))
    return dependencies_with_extras_from_markers(
        deps_with_markers=deps_with_markers,
        extras=extras,
        package_name=project.get("name", "."),
        available_extras=set(optional_deps.keys()),
    )


__all__ = [
    "resolve_extras_static",
]
