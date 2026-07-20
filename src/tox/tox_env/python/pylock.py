from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from packaging.pylock import Package, PylockValidationError
from packaging.pylock import Pylock as PackagingPylock

from tox.tox_env.errors import Fail

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from packaging.pylock import PackageArchive, PackageVcs

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

    def install_lines(self) -> list[str]:
        """Return pip requirement lines for the packages this environment locks."""
        with self.path.open("rb") as fh:
            data = tomllib.load(fh)
        try:
            parsed = PackagingPylock.from_dict(data)
        except PylockValidationError as exc:
            msg = f"invalid pylock file {self.path}: {exc}"
            raise Fail(msg) from exc
        entries = [self._to_entry(pkg) for pkg in parsed.packages if self._is_active(pkg)]
        if all(hashes for _, hashes in entries):
            # pip's hash-checking mode is all-or-nothing for a requirements file: verify when every line can carry
            # a hash, otherwise fall back to unverified installs (directory/VCS sources cannot be hashed)
            return [f"{line} {' '.join(f'--hash={h}' for h in hashes)}" for line, hashes in entries]
        return [line for line, _ in entries]

    def _is_active(self, pkg: Package) -> bool:
        env: dict[str, str | frozenset[str]] = {**self.marker_env}
        if self.extras:
            env["extras"] = self.extras
        if self.groups:
            env["dependency_groups"] = self.groups
        if pkg.marker is not None and not pkg.marker.evaluate(env, context="lock_file"):
            return False
        full_version = self.marker_env.get("python_full_version")
        if pkg.requires_python is not None and full_version is not None:
            return pkg.requires_python.contains(full_version, prereleases=True)
        return True

    def _to_entry(self, pkg: Package) -> tuple[str, list[str]]:
        """Render a locked package as a pip requirement line plus the hashes that can verify it."""
        if pkg.directory is not None:
            uri = self._to_uri(pkg.directory.path, pkg.directory.subdirectory)
            return (f"-e {uri}" if pkg.directory.editable else f"{pkg.name} @ {uri}"), []
        if pkg.vcs is not None:
            return f"{pkg.name} @ {self._to_vcs_url(pkg.vcs)}", []
        if pkg.archive is not None:
            return f"{pkg.name} @ {self._to_archive_url(pkg.archive)}", _hash_options(pkg.archive.hashes)
        line = str(pkg.name) if pkg.version is None else f"{pkg.name}=={pkg.version}"
        hashes = [
            h for dist in (pkg.sdist, *(pkg.wheels or [])) if dist is not None for h in _hash_options(dist.hashes)
        ]
        return line, hashes

    def _to_uri(self, path: str | Path, subdirectory: str | None = None) -> str:
        # PEP 751 stores paths relative to the lock file; the subdirectory is the project root within it
        target = self.path.parent / path
        if subdirectory is not None:
            target /= subdirectory
        return target.resolve().as_uri()

    def _to_vcs_url(self, vcs: PackageVcs) -> str:
        location = vcs.url if vcs.url is not None else self._to_uri(vcs.path or ".")
        revision = vcs.commit_id or vcs.requested_revision
        url = f"{vcs.type}+{location}" if revision is None else f"{vcs.type}+{location}@{revision}"
        return url if vcs.subdirectory is None else f"{url}#subdirectory={vcs.subdirectory}"

    def _to_archive_url(self, archive: PackageArchive) -> str:
        url = archive.url if archive.url is not None else self._to_uri(archive.path or ".")
        return url if archive.subdirectory is None else f"{url}#subdirectory={archive.subdirectory}"


def _hash_options(hashes: Mapping[str, str] | None) -> list[str]:
    return [f"{algorithm}:{value}" for algorithm, value in (hashes or {}).items()]


__all__ = [
    "Pylock",
]
