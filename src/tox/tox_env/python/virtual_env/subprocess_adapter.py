"""Subprocess-based virtualenv session/creator for use with pinned virtualenv versions."""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import subprocess
import sys
import venv
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Final

from filelock import FileLock
from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

from tox.tox_env.errors import Fail

if TYPE_CHECKING:
    from packaging.specifiers import SpecifierSet

_PROBE_SCRIPT: Final[str] = """\
import json, struct, sys, sysconfig
print(json.dumps({
    "implementation": sys.implementation.name,
    "version_info": list(sys.version_info[:5]),
    "version": sys.version.split()[0],
    "architecture": struct.calcsize("P") * 8,
    "platform": sys.platform,
    "system_executable": sys.executable,
    "free_threaded": sysconfig.get_config_var("Py_GIL_DISABLED") == 1,
    "debug_build": bool(sysconfig.get_config_var("Py_DEBUG")),
    "sysconfig_platform": sysconfig.get_platform(),
}))
"""


@dataclass
class _VersionInfo:
    major: int
    minor: int
    micro: int
    releaselevel: str
    serial: int


@dataclass
class SubprocessPythonInfo:
    """Python interpreter information gathered via subprocess probe."""

    implementation: str
    version_info: _VersionInfo
    version: str
    architecture: int
    platform: str
    system_executable: str
    free_threaded: bool
    debug_build: bool = False
    sysconfig_platform: str | None = None

    @property
    def machine(self) -> str:
        """Derive instruction set architecture from sysconfig_platform."""
        if (plat := self.sysconfig_platform) is None:
            return ""
        parts = plat.rsplit("-", 1)
        return parts[-1] if len(parts) > 1 else ""


@dataclass
class SubprocessCreator:
    """Mimics virtualenv Creator + Describe interface using known venv directory layout."""

    _env_dir: Path
    interpreter: SubprocessPythonInfo
    _is_win: bool = field(default_factory=lambda: sys.platform == "win32")

    @property
    def bin_dir(self) -> Path:
        return self._env_dir / ("Scripts" if self._is_win else "bin")

    @property
    def script_dir(self) -> Path:
        return self.bin_dir

    @property
    def purelib(self) -> Path:
        if self._is_win:
            return self._env_dir / "Lib" / "site-packages"
        vi = self.interpreter.version_info
        return self._env_dir / "lib" / f"python{vi.major}.{vi.minor}" / "site-packages"

    @property
    def platlib(self) -> Path:
        return self.purelib

    @property
    def exe(self) -> Path:
        return self.bin_dir / ("python.exe" if self._is_win else "python")


class SubprocessSession:
    """Mimics virtualenv Session interface, runs a bootstrapped virtualenv via subprocess."""

    def __init__(
        self,
        env_dir: Path,
        bootstrap_python: Path | None,
        env_vars: dict[str, str],
        interpreter: SubprocessPythonInfo | None,
    ) -> None:
        self._env_dir = env_dir
        self._bootstrap_python = bootstrap_python
        self._env_vars = env_vars
        self._creator = SubprocessCreator(env_dir, interpreter) if interpreter is not None else None

    def run(self) -> None:
        if self._bootstrap_python is None:
            msg = "no interpreter discovered"
            raise RuntimeError(msg)
        try:
            result = subprocess.run(
                [
                    str(self._bootstrap_python),
                    "-m",
                    "virtualenv",
                    f"--python={self.creator.interpreter.system_executable}",
                    str(self._env_dir),
                ],
                env=self._env_vars,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            msg = f"virtualenv subprocess failed: {exc}"
            raise RuntimeError(msg) from exc
        if result.returncode != 0:
            msg = f"virtualenv subprocess failed (exit {result.returncode}): {result.stderr}"
            raise RuntimeError(msg)

    @property
    def creator(self) -> SubprocessCreator:
        if self._creator is None:
            msg = "no interpreter discovered"
            raise RuntimeError(msg)
        return self._creator


def probe_python(python_path: str) -> SubprocessPythonInfo | None:
    """Probe a Python executable to extract interpreter metadata."""
    try:
        result = subprocess.run(
            [python_path, "-c", _PROBE_SCRIPT], capture_output=True, text=True, timeout=30, check=False
        )
        if result.returncode != 0:
            return None
        raw = json.loads(result.stdout)
    except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError, OSError):
        return None
    vi = raw["version_info"]
    return SubprocessPythonInfo(
        implementation=raw["implementation"],
        version_info=_VersionInfo(major=vi[0], minor=vi[1], micro=vi[2], releaselevel=vi[3], serial=vi[4]),
        version=raw["version"],
        architecture=raw["architecture"],
        platform=raw["platform"],
        system_executable=raw["system_executable"],
        free_threaded=raw["free_threaded"],
        debug_build=raw.get("debug_build", False),
        sysconfig_platform=raw.get("sysconfig_platform"),
    )


def _bootstrap_path(work_dir: Path, virtualenv_spec: str) -> Path:
    digest = hashlib.sha256(virtualenv_spec.encode()).hexdigest()[:16]
    return work_dir / ".virtualenv-bootstrap" / digest


def _bin_dir(base: Path) -> Path:
    return base / ("Scripts" if sys.platform == "win32" else "bin")


def _bootstrap_python(base: Path) -> Path:
    return _bin_dir(base) / ("python.exe" if sys.platform == "win32" else "python")


def _bootstrap_pip(base: Path) -> Path:
    return _bin_dir(base) / ("pip.exe" if sys.platform == "win32" else "pip")


def _has_correct_virtualenv(python: Path, virtualenv_spec: str) -> bool:
    if not python.exists():
        return False
    try:
        result = subprocess.run(
            [str(python), "-c", "from importlib.metadata import version; print(version('virtualenv'))"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return False
    if result.returncode != 0:
        return False
    specifier = _version_specifier(virtualenv_spec)
    return result.stdout.strip() in specifier if specifier else True


def ensure_bootstrap(work_dir: Path, virtualenv_spec: str) -> Path:
    _version_specifier(virtualenv_spec)
    base: Final[Path] = _bootstrap_path(work_dir, virtualenv_spec)
    if not base.parent.resolve().is_relative_to(work_dir.resolve()):
        cache_parent_error: Final[str] = "bootstrap cache directory must stay within work directory"
        raise Fail(cache_parent_error)
    python: Final[Path] = _bootstrap_python(base)
    if _has_correct_virtualenv(python, virtualenv_spec):
        return python

    lock_path: Final[Path] = base.parent / f"{base.name}.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(lock_path):
        if _has_correct_virtualenv(python, virtualenv_spec):
            return python
        logging.info("bootstrapping %s into %s", virtualenv_spec, base)
        if sys.platform == "win32":
            with TemporaryDirectory(dir=work_dir) as stage_parent:
                stage: Final[Path] = Path(stage_parent) / base.name
                _build_bootstrap(stage, virtualenv_spec)
                _remove_stale_bootstrap(base)
                stage.rename(base)
        else:
            _remove_stale_bootstrap(base)
            _build_bootstrap(base, virtualenv_spec)
        return python


def _build_bootstrap(base: Path, virtualenv_spec: str) -> None:
    # A planted link must fail creation; clear=True would erase its target.
    base.mkdir()
    venv.create(str(base), with_pip=True)
    result: Final[subprocess.CompletedProcess[str]] = subprocess.run(
        [str(_bootstrap_pip(base)), "install", virtualenv_spec], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        msg: Final[str] = f"failed to install {virtualenv_spec} into bootstrap env: {result.stderr}"
        raise RuntimeError(msg)


def _remove_stale_bootstrap(base: Path) -> None:
    if base.is_symlink() or (base.exists() and not base.is_dir()):
        base.unlink()
    elif base.exists():
        shutil.rmtree(base)


def _version_specifier(virtualenv_spec: str) -> SpecifierSet:
    msg = "virtualenv_spec must name virtualenv with optional version specifiers"
    try:
        requirement = Requirement(virtualenv_spec)
    except InvalidRequirement:
        raise Fail(msg) from None
    if (
        canonicalize_name(requirement.name) != "virtualenv"
        or requirement.url is not None
        or requirement.extras
        or requirement.marker is not None
        or any(specifier.operator == "===" for specifier in requirement.specifier)
    ):
        raise Fail(msg)
    return requirement.specifier


__all__ = [
    "SubprocessCreator",
    "SubprocessPythonInfo",
    "SubprocessSession",
    "ensure_bootstrap",
    "probe_python",
]
