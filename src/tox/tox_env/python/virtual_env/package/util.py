from __future__ import annotations

from copy import deepcopy

from packaging.markers import Variable
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
        _at: int | None = None
        extra_markers = set()
        for _at, (marker_key, op, marker_value) in (
            (_at_marker, marker)
            for _at_marker, marker in enumerate(markers)
            if isinstance(marker, tuple) and len(marker) == 3
        ):
            if marker_key.value == "extra" and op.value == "==":  # pragma: no branch
                extra_markers.add(marker_value.value)
                del markers[_at]
                _at -= 1
                if _at > 0 and (isinstance(markers[_at], str) and markers[_at] in ("and", "or")):
                    del markers[_at]
                if len(markers) == 0:
                    req.marker = None
                break
        result.append((req, extra_markers or {None}))
    return result
