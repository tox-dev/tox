from __future__ import annotations

from copy import deepcopy

from packaging.markers import Variable  # type: ignore[attr-defined]
from packaging.requirements import Requirement


def dependencies_with_extras(deps: list[Requirement], extras: set[str], package_name: str) -> list[Requirement]:
    deps_with_markers = extract_extra_markers(deps)
    result: list[Requirement] = []
    found: set[str] = set()
    todo: set[str | None] = extras | {None}
    visited: set[str | None] = set()
    while todo:
        new_extras: set[str | None] = set()
        for req, extra_markers in deps_with_markers:
            if todo & extra_markers:
                if req.name == package_name:  # support for recursive extras
                    new_extras.update(req.extras or set())
                else:
                    req_str = str(req)
                    if req_str not in found:
                        found.add(req_str)
                        result.append(req)
        visited.update(todo)
        todo = new_extras - visited
    return result


def extract_extra_markers(deps: list[Requirement]) -> list[tuple[Requirement, set[str | None]]]:
    # extras might show up as markers, move them into extras property
    result: list[tuple[Requirement, set[str | None]]] = []
    for req in deps:
        req = deepcopy(req)
        markers: list[str | tuple[Variable, Variable, Variable]] = getattr(req.marker, "_markers", []) or []
        new_markers: list[str | tuple[Variable, Variable, Variable]] = []

        def _is_extra_marker(_marker) -> bool:
            return (
                isinstance(_marker, tuple)
                and len(_marker) == 3
                and _marker[0].value == "extra"
                and _marker[1].value == "=="
            )

        extra_markers = set()
        marker = markers.pop(0) if markers else None
        while marker:
            if _is_extra_marker(marker):
                extra_markers.add(marker[2].value)
                if new_markers and new_markers[-1] in ("and", "or"):
                    del new_markers[-1]
                marker = markers.pop(0) if markers else None
                if marker in ("and", "or"):
                    marker = markers.pop(0) if markers else None
            else:
                new_markers.append(marker)
                marker = markers.pop(0) if markers else None
        if new_markers:
            req.marker._markers = new_markers
        else:
            req.marker = None
        result.append((req, extra_markers or {None}))
    return result
