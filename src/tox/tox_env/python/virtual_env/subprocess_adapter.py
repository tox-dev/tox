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
    from python_discovery import MarkerEnvironment


class SubprocessSession:
    """Mimics virtualenv Session interface, runs a bootstrapped virtualenv via subprocess.

    :param env_dir: the directory of the virtual environment
    :param bootstrap_python: the Python used to bootstrap the environment, if any
    :param env_vars: the environment variables of the subprocess
    :param interpreter: the Python interpreter of the environment, if known

    """

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
        self._creator = (
            SubprocessCreator(_env_dir=env_dir, interpreter=interpreter) if interpreter is not None else None
        )

    def run(self) -> None:
        """Run the create step of the environment in a subprocess.

        :raises RuntimeError: when no bootstrap interpreter was found

        """
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
        """The creator of the environment, which describes its paths.

        :raises RuntimeError: when no interpreter was discovered

        """
        if self._creator is None:
            msg = "no interpreter discovered"
            raise RuntimeError(msg)
        return self._creator


@dataclass(frozen=True, slots=True, kw_only=True)
class SubprocessCreator:
    """Mimics virtualenv Creator + Describe interface using known venv directory layout.

    :param interpreter: the Python interpreter the virtual environment is created with

    """

    _env_dir: Path
    interpreter: SubprocessPythonInfo
    _is_win: bool = field(default_factory=lambda: sys.platform == "win32")

    @property
    def script_dir(self) -> Path:
        """The directory the scripts of the environment are placed in, the same as its bin directory."""
        return self.bin_dir

    @property
    def bin_dir(self) -> Path:
        """The directory the executables of the environment are placed in."""
        return self._env_dir / ("Scripts" if self._is_win else "bin")

    @property
    def platlib(self) -> Path:
        """The directory of the platform specific libraries of the environment, the same as its purelib directory."""
        return self.purelib

    @property
    def purelib(self) -> Path:
        """The directory of the pure python libraries of the environment."""
        if self._is_win:
            return self._env_dir / "Lib" / "site-packages"
        vi = self.interpreter.version_info
        return self._env_dir / "lib" / f"python{vi.major}.{vi.minor}" / "site-packages"

    @property
    def exe(self) -> Path:
        """The python executable of the environment."""
        return self.bin_dir / ("python.exe" if self._is_win else "python")


def probe_python(python_path: str, marker_environment: MarkerEnvironment | None = None) -> SubprocessPythonInfo | None:
    """Probe a python interpreter for its details, by running it.

    :param python_path: the path of the interpreter
    :param marker_environment: the marker environment to compare the interpreter with, ``None`` to skip it

    :returns: the details, or ``None`` when the interpreter cannot be probed

    """
    probe_script: str = """\
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
    try:
        result = subprocess.run(
            [python_path, "-c", probe_script], capture_output=True, text=True, timeout=30, check=False
        )
        if result.returncode != 0:
            return None
        raw = json.loads(result.stdout)
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
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
        marker_environment=marker_environment,
        debug_build=raw.get("debug_build", False),
        sysconfig_platform=raw.get("sysconfig_platform"),
    )


@dataclass(slots=True, kw_only=True)
class SubprocessPythonInfo:
    """The details of a python interpreter, probed by running it in a subprocess.

    :param implementation: the name of the implementation
    :param version_info: the version of the interpreter
    :param version: the full version string
    :param architecture: the number of bits of the interpreter
    :param platform: the platform the interpreter runs on
    :param system_executable: the path of the system executable of the interpreter
    :param free_threaded: whether the interpreter is a free-threaded build
    :param debug_build: whether the interpreter is a debug build
    :param sysconfig_platform: the platform name from ``sysconfig``, ``None`` when unknown
    :param marker_environment: the environment markers of the interpreter, ``None`` when unknown

    """

    implementation: str
    version_info: _VersionInfo
    version: str
    architecture: int
    platform: str
    system_executable: str
    free_threaded: bool
    debug_build: bool = False
    sysconfig_platform: str | None = None
    marker_environment: MarkerEnvironment | None = None

    @property
    def machine(self) -> str:
        """Derive instruction set architecture from sysconfig_platform."""
        if (plat := self.sysconfig_platform) is None:
            return ""
        parts = plat.rsplit("-", 1)
        return parts[-1] if len(parts) > 1 else ""


@dataclass(slots=True, kw_only=True, frozen=True)
class _VersionInfo:
    major: int
    minor: int
    micro: int
    releaselevel: str
    serial: int


def ensure_bootstrap(work_dir: Path, virtualenv_spec: str) -> Path:
    """Make sure the virtualenv used to create environments is available.

    :param work_dir: the directory the bootstrap is kept in
    :param virtualenv_spec: the requirement of the virtualenv to bootstrap

    :returns: the path of the bootstrap

    :raises tox.tox_env.errors.Fail: when the cache directory of the bootstrap cannot be created

    """
    _version_specifier(virtualenv_spec)
    base: Final[Path] = _bootstrap_path(work_dir, virtualenv_spec)
    if not base.parent.resolve().is_relative_to(work_dir.resolve()):
        cache_parent_error: Final[str] = "bootstrap cache directory must stay within work directory"
        raise Fail(cache_parent_error)
    python: Final[Path] = _bin_dir(base) / ("python.exe" if sys.platform == "win32" else "python")
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


def _bootstrap_path(work_dir: Path, virtualenv_spec: str) -> Path:
    return work_dir / ".virtualenv-bootstrap" / hashlib.sha256(virtualenv_spec.encode()).hexdigest()[:16]


def _bin_dir(base: Path) -> Path:
    return base / ("Scripts" if sys.platform == "win32" else "bin")


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
    except (subprocess.SubprocessError, OSError):
        return False
    if result.returncode != 0:
        return False
    specifier = _version_specifier(virtualenv_spec)
    return result.stdout.strip() in specifier if specifier else True


def _build_bootstrap(base: Path, virtualenv_spec: str) -> None:
    # A planted link must fail creation; clear=True would erase its target.
    base.mkdir()
    venv.create(str(base), with_pip=True)
    result: Final[subprocess.CompletedProcess[str]] = subprocess.run(
        [str(_bin_dir(base) / ("pip.exe" if sys.platform == "win32" else "pip")), "install", virtualenv_spec],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        msg: Final[str] = f"failed to install {virtualenv_spec} into bootstrap env: {result.stderr}"
        raise RuntimeError(msg)


def _remove_stale_bootstrap(base: Path) -> None:
    if base.is_symlink() or (base.exists() and not base.is_dir()):
        base.unlink()
    elif base.exists():
        shutil.rmtree(base)


__all__ = [
    "SubprocessCreator",
    "SubprocessPythonInfo",
    "SubprocessSession",
    "ensure_bootstrap",
    "probe_python",
]
