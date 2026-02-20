from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from packaging.pylock import Package, PylockValidationError
from packaging.pylock import Pylock as PackagingPylock
from packaging.requirements import Requirement

from tox.tox_env.errors import Fail

if TYPE_CHECKING:
    from pathlib import Path

if sys.version_info >= (3, 11):  # pragma: no cover
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib


@dataclass(frozen=True, kw_only=True)
class Pylock:
    path: Path

    def requirements(self) -> list[Requirement]:
        with self.path.open("rb") as fh:
            data = tomllib.load(fh)
        try:
            parsed = PackagingPylock.from_dict(data)
        except PylockValidationError as exc:
            msg = f"invalid pylock file {self.path}: {exc}"
            raise Fail(msg) from exc
        return [self._to_requirement(pkg) for pkg in parsed.packages]

    @staticmethod
    def _to_requirement(pkg: Package) -> Requirement:
        req_str = str(pkg.name)
        if pkg.version is not None:
            req_str += f"=={pkg.version}"
        if pkg.marker is not None:
            req_str += f"; {pkg.marker}"
        return Requirement(req_str)


@dataclass(frozen=True, kw_only=True)
class Pylocks:
    locks: tuple[Pylock, ...]

    def requirements(self) -> list[Requirement]:
        return [req for lock in self.locks for req in lock.requirements()]


__all__ = [
    "Pylock",
    "Pylocks",
]
