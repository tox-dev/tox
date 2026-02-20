"""Subprocess-based virtualenv session/creator for use with pinned virtualenv versions."""

from __future__ import annotations

import hashlib
import json
import logging
import subprocess
import sys
import venv
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from filelock import FileLock

if TYPE_CHECKING:
    from pathlib import Path


_PROBE_SCRIPT = """\
import json, struct, sys, sysconfig
print(json.dumps({
    "implementation": sys.implementation.name,
    "version_info": list(sys.version_info[:5]),
    "version": sys.version.split()[0],
    "architecture": struct.calcsize("P") * 8,
    "platform": sys.platform,
    "system_executable": sys.executable,
    "free_threaded": sysconfig.get_config_var("Py_GIL_DISABLED") == 1,
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
        bootstrap_python: Path,
        env_vars: dict[str, str],
        interpreter: SubprocessPythonInfo | None,
    ) -> None:
        self._env_dir = env_dir
        self._bootstrap_python = bootstrap_python
        self._env_vars = env_vars
        self._creator = SubprocessCreator(env_dir, interpreter) if interpreter is not None else None

    def run(self) -> None:
        cmd = [str(self._bootstrap_python), "-m", "virtualenv", str(self._env_dir)]
        try:
            result = subprocess.run(cmd, env=self._env_vars, capture_output=True, text=True, check=False)
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
        if result.returncode != 0:
            return False
        from packaging.specifiers import SpecifierSet  # noqa: PLC0415

        installed = result.stdout.strip()
        spec = virtualenv_spec.removeprefix("virtualenv")
        return installed in SpecifierSet(spec) if spec else True
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return False


def ensure_bootstrap(work_dir: Path, virtualenv_spec: str) -> Path:
    """Create or reuse a cached bootstrap venv with the specified virtualenv version."""
    base = _bootstrap_path(work_dir, virtualenv_spec)
    python = _bootstrap_python(base)
    if _has_correct_virtualenv(python, virtualenv_spec):
        return python

    lock_path = base.parent / f"{base.name}.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(lock_path):
        if _has_correct_virtualenv(python, virtualenv_spec):
            return python
        logging.info("bootstrapping %s into %s", virtualenv_spec, base)
        if base.exists():
            import shutil  # noqa: PLC0415

            shutil.rmtree(base)
        venv.create(str(base), with_pip=True, clear=True)
        pip = _bootstrap_pip(base)
        result = subprocess.run([str(pip), "install", virtualenv_spec], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            msg = f"failed to install {virtualenv_spec} into bootstrap env: {result.stderr}"
            raise RuntimeError(msg)
        return python
