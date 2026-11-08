from __future__ import annotations  # simplint: ignore[SMP104]  # extras resolution and sdist extraction for the builder

import tarfile
from copy import deepcopy
from pathlib import PurePath
from typing import TYPE_CHECKING, Final, Literal, cast

from packaging.markers import Marker
from packaging.utils import canonicalize_name

from tox.tox_env.errors import Fail

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from packaging._parser import MarkerAtom, MarkerList, Op, Value, Variable
    from packaging.requirements import Requirement


def dependencies_with_extras(
    deps: list[Requirement],
    extras: set[str],
    package_name: str,
    *,
    available_extras: set[str] | None = None,
) -> list[Requirement]:
    """Get the dependencies that apply to the requested extras of a package.

    :param deps: the dependencies of the package
    :param extras: the requested extras
    :param package_name: the name of the package the dependencies belong to
    :param available_extras: the extras the package provides, ``None`` when unknown

    :returns: the dependencies that apply

    """
    return dependencies_with_extras_from_markers(
        [extract_extra_markers(dep) for dep in deps], extras, package_name, available_extras=available_extras
    )


def dependencies_with_extras_from_markers(  # simplint: ignore[SMP403]  # imported by tox plugins
    deps_with_markers: list[tuple[Requirement, set[str | None]]],
    extras: set[str],
    package_name: str,
    *,
    available_extras: set[str] | None = None,
) -> list[Requirement]:
    """Get the dependencies that apply to the requested extras, from their markers.

    :param deps_with_markers: the dependencies, each with the extras its marker selects
    :param extras: the requested extras
    :param package_name: the name of the package the dependencies belong to
    :param available_extras: the extras the package provides, ``None`` when unknown

    :returns: the dependencies that apply

    :raises tox.tox_env.errors.Fail: when a requested extra is not provided by the package

    """
    normalized_extras = _check_available_extras(extras, available_extras, package_name)
    result: Final[list[Requirement]] = []
    found: Final[set[str]] = set()
    normalized_package_name: Final[str] = canonicalize_name(package_name)
    # Distinct marker paths to one extra can produce distinct requirements.
    todo: set[tuple[str | None, frozenset[Marker]]] = {(extra, frozenset()) for extra in normalized_extras | {None}}
    visited: Final[set[tuple[str | None, frozenset[Marker]]]] = set()
    while todo:
        new_extras: set[tuple[str | None, frozenset[Marker]]] = set()
        # Set iteration order must not change dependency order.
        ordered_todo = sorted(todo, key=_by_extra_and_markers)
        for req, extra_markers in deps_with_markers:
            for extra, via in ordered_todo:
                if extra not in extra_markers:
                    continue
                if canonicalize_name(req.name) == normalized_package_name:
                    nested = via | {req.marker} if req.marker is not None else via
                    new_extras.update((canonicalize_name(extra_name), nested) for extra_name in req.extras)
                else:
                    _add_dependency(req, via, result, found)
        visited.update(todo)
        todo = new_extras - visited
    return result


def _check_available_extras(extras: set[str], available_extras: set[str] | None, package_name: str) -> set[str]:
    normalized_extras: Final[set[str]] = {canonicalize_name(extra) for extra in extras}
    if available_extras is not None and normalized_extras:
        normalized_available: Final[set[str]] = {canonicalize_name(extra) for extra in available_extras}
        if unknown := normalized_extras - normalized_available:
            available_str = ", ".join(sorted(normalized_available)) or "none"
            unknown_str = ", ".join(sorted(unknown))
            msg = f"extras not found for package {package_name}: {unknown_str} (available: {available_str})"
            raise Fail(msg)
    return normalized_extras


def _by_extra_and_markers(state: tuple[str | None, frozenset[Marker]]) -> tuple[str, tuple[str, ...]]:
    return state[0] or "", tuple(sorted(str(marker) for marker in state[1]))


def _add_dependency(req: Requirement, via: frozenset[Marker], result: list[Requirement], found: set[str]) -> None:
    dep = deepcopy(req) if via else req
    if via:
        dep.marker = Marker(
            " and ".join(f"({marker})" for marker in (*sorted(via, key=str), req.marker) if marker is not None)
        )
    if (dep_str := str(dep)) not in found:
        found.add(dep_str)
        result.append(dep)


def extract_extra_markers(req: Requirement) -> tuple[Requirement, set[str | None]]:
    req = deepcopy(req)
    markers: MarkerList = getattr(req.marker, "_markers", []) or []
    new_markers, extra_markers = _split_extra_markers(markers)
    if new_markers:
        cast("Marker", req.marker)._markers = new_markers  # ruff:ignore[private-member-access]  # internal access
    else:
        req.marker = None
    return req, extra_markers or {None}


def _split_extra_markers(markers: MarkerList) -> tuple[MarkerList, set[str | None]]:
    new_markers: MarkerList = []
    extra_markers: set[str | None] = set()
    while markers:
        marker = markers.pop(0)
        if (extra := _get_extra(marker)) is not None:
            extra_markers.add(canonicalize_name(extra))
            if new_markers and new_markers[-1] in {"and", "or"}:
                del new_markers[-1]
            if markers and markers[0] in {"and", "or"}:
                markers.pop(0)
        else:
            new_markers.append(marker)
    return new_markers, extra_markers


def _get_extra(
    _marker: MarkerList | tuple[Variable | Value, Op, Variable | Value] | Sequence[MarkerAtom] | Literal["and", "or"],
) -> str | None:
    # the marker tuple is (lhs, op, rhs)
    if not isinstance(_marker, tuple) or len(_marker) != 3:  # ruff:ignore[magic-value-comparison]
        return None
    left, op, right = cast("tuple[Variable | Value, Op, Variable | Value]", _marker)
    if hasattr(left, "value") and left.value == "extra" and hasattr(op, "value") and op.value == "==":
        return right.value if hasattr(right, "value") else None
    return None


def safe_extractall(tar: tarfile.TarFile, path: Path) -> None:
    """Extract a tar archive, refusing members that would land outside the target directory.

    :param tar: the archive to extract
    :param path: the directory to extract into

    :raises tox.tox_env.errors.Fail: when a member of the archive cannot be extracted safely

    """
    if hasattr(tarfile, "data_filter"):
        try:
            tar.extractall(path=str(path), filter="data")
        except tarfile.FilterError as exc:
            msg = f"cannot extract tar member {exc.tarinfo.name!r} into {path}: {exc}"
            raise Fail(msg) from exc
    else:
        # extract one member at a time so each check resolves links created by earlier members
        dest: Final[Path] = path.resolve()

        for member in tar.getmembers():
            target: Path = dest / member.name
            inside_dest: bool = target.resolve().is_relative_to(dest)
            if inside_dest and (member.issym() or member.islnk()):
                link: PurePath = PurePath(member.linkname)
                base: Path = target.parent if member.issym() else dest
                inside_dest = not link.anchor and (base / link).resolve().is_relative_to(dest)
            if not inside_dest:
                msg = f"cannot extract tar member {member.name!r} into {path}: path escapes destination"
                raise Fail(msg)
            tar.extract(member, path=str(dest))


__all__ = [
    "dependencies_with_extras",
    "dependencies_with_extras_from_markers",
    "safe_extractall",
]
