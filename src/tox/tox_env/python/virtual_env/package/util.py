from __future__ import annotations

from copy import deepcopy

from packaging.markers import Variable
from packaging.requirements import Requirement


def dependencies_with_extras(deps: list[Requirement], extras: set[str], package_name: str) -> list[Requirement]:
    deps = _normalize_req(deps)
    result: list[Requirement] = []
    found: set[str] = set()
    todo: set[str | None] = extras | {None}
    visited: set[str | None] = set()
    while todo:
        new_extras: set[str | None] = set()
        for req in deps:
            if todo & (req.extras or {None}):  # type: ignore[arg-type]
                if req.name == package_name:  # support for recursive extras
                    new_extras.update(req.extras or set())
                else:
                    req = deepcopy(req)
                    req.extras.clear()  # strip the extra part as the installation will invoke it without
                    req_str = str(req)
                    if req_str not in found:
                        found.add(req_str)
                        result.append(req)
        visited.update(todo)
        todo = new_extras - visited
    return result


def _normalize_req(deps: list[Requirement]) -> list[Requirement]:
    # extras might show up as markers, move them into extras property
    result: list[Requirement] = []
    for req in deps:
        req = deepcopy(req)
        markers: list[str | tuple[Variable, Variable, Variable]] = getattr(req.marker, "_markers", []) or []
        _at: int | None = None
        for _at, (marker_key, op, marker_value) in (
            (_at_marker, marker)
            for _at_marker, marker in enumerate(markers)
            if isinstance(marker, tuple) and len(marker) == 3
        ):
            if marker_key.value == "extra" and op.value == "==":  # pragma: no branch
                req.extras.add(marker_value.value)
                del markers[_at]
                _at -= 1
                if _at > 0 and (isinstance(markers[_at], str) and markers[_at] in ("and", "or")):
                    del markers[_at]
                if len(markers) == 0:
                    req.marker = None
                break
        result.append(req)
    return result
