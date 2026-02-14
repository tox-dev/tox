from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Literal, cast

if TYPE_CHECKING:
    from collections.abc import Sequence

    from packaging._parser import Op, Value, Variable
    from packaging.markers import Marker, MarkerAtom, MarkerList
    from packaging.requirements import Requirement


def dependencies_with_extras(deps: list[Requirement], extras: set[str], package_name: str) -> list[Requirement]:
    return dependencies_with_extras_from_markers(extract_extra_markers(deps), extras, package_name)


def dependencies_with_extras_from_markers(
    deps_with_markers: list[tuple[Requirement, set[str | None]]],
    extras: set[str],
    package_name: str,
) -> list[Requirement]:
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
    """
    Extract extra markers from dependencies.

    :param deps: the dependencies
    :return: a list of requirement, extras set
    """
    return [_extract_extra_markers(d) for d in deps]


def _extract_extra_markers(req: Requirement) -> tuple[Requirement, set[str | None]]:
    req = deepcopy(req)
    markers: MarkerList = getattr(req.marker, "_markers", []) or []
    new_markers: MarkerList = []
    extra_markers: set[str] = set()
    marker = markers.pop(0) if markers else None
    while marker:
        extra = _get_extra(marker)
        if extra is not None:
            extra_markers.add(extra)
            if new_markers and new_markers[-1] in {"and", "or"}:
                del new_markers[-1]
            marker = markers.pop(0) if markers else None
            if marker in {"and", "or"}:
                marker = markers.pop(0) if markers else None
        else:
            new_markers.append(marker)
            marker = markers.pop(0) if markers else None
    if new_markers:
        cast("Marker", req.marker)._markers = new_markers  # noqa: SLF001
    else:
        req.marker = None
    return req, cast("set[str | None]", extra_markers) or {None}


def _get_extra(
    _marker: MarkerList | tuple[Variable | Value, Op, Variable | Value] | Sequence[MarkerAtom] | Literal["and", "or"],
) -> str | None:
    if not isinstance(_marker, tuple) or len(_marker) != 3:  # noqa: PLR2004
        return None
    marker_tuple = cast("tuple[Variable | Value, Op, Variable | Value]", _marker)
    left, op, right = marker_tuple
    if hasattr(left, "value") and left.value == "extra" and hasattr(op, "value") and op.value == "==":
        return right.value if hasattr(right, "value") else None
    return None
