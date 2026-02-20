from __future__ import annotations

import sys
from dataclasses import dataclass, field
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
    extras: frozenset[str] = frozenset()
    groups: frozenset[str] = frozenset()
    marker_env: dict[str, str] = field(default_factory=dict)

    def requirements(self) -> list[Requirement]:
        with self.path.open("rb") as fh:
            data = tomllib.load(fh)
        try:
            parsed = PackagingPylock.from_dict(data)
        except PylockValidationError as exc:
            msg = f"invalid pylock file {self.path}: {exc}"
            raise Fail(msg) from exc
        env: dict[str, str | frozenset[str]] = {**self.marker_env}
        if self.extras:
            env["extras"] = self.extras
        if self.groups:
            env["dependency_groups"] = self.groups
        return [
            self._to_requirement(pkg)
            for pkg in parsed.packages
            if pkg.marker is None or pkg.marker.evaluate(env, context="lock_file")
        ]

    @staticmethod
    def _to_requirement(pkg: Package) -> Requirement:
        req_str = str(pkg.name)
        if pkg.version is not None:
            req_str += f"=={pkg.version}"
        return Requirement(req_str)


__all__ = [
    "Pylock",
]
