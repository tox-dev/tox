"""Declare the abstract base class for tox environments that handle the Python language."""

from __future__ import annotations

import logging
import re
import sys
import sysconfig
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, NamedTuple

from virtualenv.discovery.py_spec import PythonSpec

from tox.config.loader.str_convert import StrConvert
from tox.tox_env.api import ToxEnv, ToxEnvCreateArgs
from tox.tox_env.errors import Fail, Recreate, Skip
from tox.util.typing_compat import override

if TYPE_CHECKING:
    from io import TextIOWrapper

    from python_discovery import MarkerEnvironment

    from tox.config.cli.parser import Parsed
    from tox.config.main import Config
    from tox.config.sets import CoreConfigSet, EnvConfigSet
    from tox.util.json_types import JsonValue


class VersionInfo(NamedTuple):
    """The version of a python interpreter, the same as ``sys.version_info``.

    :param major: the major version
    :param minor: the minor version
    :param micro: the micro version
    :param releaselevel: the release level, such as ``final``
    :param serial: the serial of the release level

    """

    major: int
    minor: int
    micro: int
    releaselevel: str
    serial: int


@dataclass(frozen=True, slots=True)
class PythonInfo:
    """The details of a python interpreter that tox uses to create an environment.

    :param implementation: the name of the implementation, such as ``CPython``
    :param version_info: the version of the interpreter
    :param version: the full version string
    :param is_64: whether the interpreter is a 64-bit build
    :param platform: the platform the interpreter runs on
    :param extra: the extra details that the interpreter reports
    :param free_threaded: whether the interpreter is a free-threaded build
    :param debug: whether the interpreter is a debug build
    :param machine: the machine architecture
    :param marker_environment: the environment markers of the interpreter, ``None`` when unknown

    """

    implementation: str
    version_info: VersionInfo
    version: str
    is_64: bool
    platform: str
    extra: dict[str, Any]
    free_threaded: bool = False
    debug: bool = False
    machine: str | None = None
    marker_environment: MarkerEnvironment | None = None

    @property
    def version_no_dot(self) -> str:
        """The major and minor version without a dot, such as ``313``."""
        return f"{self.version_info.major}{self.version_info.minor}"

    @property
    def impl_lower(self) -> str:
        """The name of the implementation in lower case, such as ``cpython``."""
        return self.implementation.lower()

    @property
    def version_dot(self) -> str:
        """The major and minor version with a dot, such as ``3.13``."""
        return f"{self.version_info.major}.{self.version_info.minor}"


_PY_FACTORS_RE: Final[re.Pattern[str]] = re.compile(
    r"""
    ^(?!py$)                                               # don't match 'py' as it doesn't provide any info
    (?P<impl>py|pypy|cpython|jython|graalpy|rustpython|ironpython) # the interpreter; most users will simply use 'py'
    (?:
    (?P<version>[2-9]\.?[0-9]?[0-9]?)                      # the version; one of: MAJORMINOR, MAJOR.MINOR
    (?P<threaded>t?)                                       # version followed by t for free-threading
    (?P<debug>d?)                                          # version followed by d for a debug build
    )?$
    """,
    re.VERBOSE,
)
_PY_FACTORS_RE_EXPLICIT_VERSION: Final[re.Pattern[str]] = re.compile(
    r"""
    ^
    ( (?P<impl> cpython | pypy ) - )?   # optional interpreter prefix with dash
    (?P<version> [23] \. [0-9]+ )        # explicit major.minor version (Python 2.x or 3.x)
    (?P<threaded> t? )                   # optional free-threaded suffix
    (?P<debug> d? )                      # optional debug-build suffix
    $
    """,
    re.VERBOSE,
)


class Python(ToxEnv, ABC):
    """The base of the tox environments that use a python interpreter.

    :param create_args: the arguments the environment is created with

    """

    def __init__(self, create_args: ToxEnvCreateArgs) -> None:
        self._base_python: PythonInfo | None = None
        self._base_python_searched: bool = False
        super().__init__(create_args)

    @override
    def register_config(self) -> None:
        super().register_config()

        def _ensure_list(value: list[str] | str) -> list[str]:
            return [value] if isinstance(value, str) else value

        self.conf.add_config(
            keys=["default_base_python"],
            of_type=list[str] | str,
            default=[sys.executable],
            desc="fallback python interpreter used when no factor or explicit base_python is defined",
            post_process=_ensure_list,
        )

        self.conf.add_config(
            keys=["base_python_file"],
            of_type=list[str] | str,
            default=[],
            desc="file(s) containing the Python version to use (e.g. .python-version), first one found wins; "
            "used when base_python is not explicitly set and the env name has no Python factor",
            post_process=_ensure_list,
        )

        self._base_python_explicitly_set = True  # track whether base_python was explicitly configured

        def validate_base_python(value: list[str] | str) -> list[str]:
            result: Final[list[str]] = [entry for entry in _ensure_list(value) if entry.strip()]
            if self._base_python_explicitly_set and self.conf["base_python_file"]:
                msg = "cannot set both base_python and base_python_file"
                raise Fail(msg)
            if self._base_python_explicitly_set and not result:
                empty_spec_message: Final[str] = f"base_python for env {self.name} is empty"
                raise Fail(empty_spec_message)
            return self._validate_base_python(self.name, result, self.core["ignore_base_python_conflict"])

        self.conf.add_config(
            keys=["base_python", "basepython"],
            of_type=list[str] | str,
            default=self._base_python_default,
            desc="environment identifier for python, first one found wins",
            post_process=validate_base_python,
        )
        self.core.add_config(
            keys=["ignore_base_python_conflict", "ignore_basepython_conflict"],
            of_type=bool,
            default=False,
            desc="do not raise error if the environment name conflicts with base python",
        )
        self.conf.add_constant(
            keys=["env_site_packages_dir", "envsitepackagesdir"],
            desc="the python environments site package - pure python (purelib)",
            value=self.env_site_package_dir,
        )
        self.conf.add_constant(
            keys=["env_site_packages_dir_plat", "envsitepackagesdir_plat"],
            desc="the python environments platform-specific site package (platlib)",
            value=self.env_site_package_dir_plat,
        )
        self.conf.add_constant(
            keys=["env_bin_dir", "envbindir"],
            desc="the python environments binary folder",
            value=self.env_bin_dir,
        )
        self.conf.add_constant(
            ["env_python", "envpython"],
            desc="python executable from within the tox environment",
            value=self.env_python,
        )
        self.conf.add_constant("py_dot_ver", "<python major>.<python minor>", value=self.py_dot_ver)
        self.conf.add_constant("py_impl", "python implementation", value=self.py_impl)
        self.conf.add_constant("py_free_threaded", "is no-gil interpreted", value=self.py_free_threaded)
        self.conf.add_constant("py_debug", "is a debug build", value=self.py_debug)

    @classmethod
    def _validate_base_python(
        cls,
        env_name: str,
        base_pythons: list[str],
        ignore_base_python_conflict: bool,  # ruff:ignore[boolean-type-hint-positional-argument]  # keeps the signature
    ) -> list[str]:
        try:
            env_base_python = cls.extract_base_python(env_name)
        except ValueError:
            if ignore_base_python_conflict:
                return base_pythons
            raise
        if env_base_python is not None:
            spec_name = PythonSpec.from_string_spec(env_base_python)
            for base_python in base_pythons:
                if cls._conflicts(spec_name, cls._resolve_base_spec(base_python)):
                    msg = f"env name {env_name} conflicting with base python {base_python}"
                    if ignore_base_python_conflict:
                        # ignore the base python settings and return the thing that looks like a Python version
                        return [env_base_python]
                    raise Fail(msg)
        return base_pythons

    @classmethod
    def extract_base_python(cls, env_name: str) -> str | None:
        """Extract the python specification from an environment name, such as ``py313`` from ``py313-test``.

        :param env_name: the name of the environment

        :returns: the python specification, or ``None`` when the name does not contain one

        :raises ValueError: when the name contains more than one python specification

        """
        candidates: list[str] = []
        if match := _PY_FACTORS_RE_EXPLICIT_VERSION.match(env_name):
            candidates.append(cls._explicit_version_spec(match.groupdict()))
        else:
            for factor in env_name.split("-"):
                if match := _PY_FACTORS_RE.match(factor):
                    candidates.append(factor)
                elif match := _PY_FACTORS_RE_EXPLICIT_VERSION.match(factor):
                    candidates.append(cls._explicit_version_spec(match.groupdict()))
        if candidates:
            if len(candidates) > 1:
                msg = f"conflicting factors {', '.join(candidates)} in {env_name}"
                raise ValueError(msg)
            return next(iter(candidates))
        return None

    @staticmethod
    def _explicit_version_spec(found: dict[str, str | None]) -> str:
        return f"{('pypy' if found['impl'] == 'pypy' else '')}{found['version']}{found['threaded']}{found['debug']}"

    @staticmethod
    def _conflicts(spec_name: PythonSpec, spec_base: PythonSpec) -> bool:
        implementation_conflict = spec_name.implementation is not None and (
            spec_base.implementation is None or spec_base.implementation.lower() != spec_name.implementation.lower()
        )
        return implementation_conflict or any(
            getattr(spec_base, key) != getattr(spec_name, key)
            for key in (
                "major",
                "minor",
                "micro",
                "architecture",
                "machine",
                "free_threaded",
                "debug",
            )
            if getattr(spec_name, key) is not None
        )

    @classmethod
    def _resolve_base_spec(cls, base_python: str) -> PythonSpec:
        spec_base = PythonSpec.from_string_spec(base_python)
        if spec_base.path is None:
            return spec_base
        if str(spec_base.path) == sys.executable:
            return cls._python_spec_for_sys_executable()
        return cls.python_spec_for_path(Path(spec_base.path).absolute())

    @classmethod
    def _python_spec_for_sys_executable(cls) -> PythonSpec:
        implementation = sys.implementation.name
        version = sys.version_info
        bits = "64" if sys.maxsize > 2**32 else "32"
        threaded = "t" if sysconfig.get_config_var("Py_GIL_DISABLED") == 1 else ""
        debug = "d" if sysconfig.get_config_var("Py_DEBUG") else ""
        parts = sysconfig.get_platform().rsplit("-", 1)
        machine_suffix = f"-{isa}" if len(parts) > 1 and (isa := parts[-1]) else ""
        string_spec = f"{implementation}{version.major}{version.minor}{threaded}{debug}-{bits}{machine_suffix}"
        return PythonSpec.from_string_spec(string_spec)

    @classmethod
    @abstractmethod
    def python_spec_for_path(cls, path: Path) -> PythonSpec:
        """Get the spec for an absolute path to a Python executable.

        :param path: the path investigated

        :returns: the found spec

        """
        raise NotImplementedError

    def _base_python_default(  # override signature
        self,
        conf: Config,  # ruff:ignore[unused-method-argument]  # override signature
        env_name: str | None,  # override signature
    ) -> list[str]:
        self._base_python_explicitly_set = False
        try:
            base_python = None if env_name is None else self.extract_base_python(env_name)
        except ValueError:
            if self.core["ignore_base_python_conflict"]:
                base_python = None
            else:
                raise
        if base_python is not None:
            return [base_python]
        if base_python_files := self.conf.get("base_python_file", list[str]):
            return self._read_python_version_file(base_python_files)
        return self.conf.get("default_base_python", list[str])

    def _read_python_version_file(self, file_paths: list[str]) -> list[str]:
        tox_root = self.core.get("toxinidir", Path)
        for file_path in file_paths:
            path = tox_root / file_path
            if not path.exists():
                continue
            if not path.is_file():
                msg = f"base_python_file: {file_path!r} is not a regular file"
                raise Fail(msg)
            try:
                version = self._first_version_line(path, file_path)
            except (OSError, UnicodeDecodeError) as exc:
                msg = f"base_python_file: cannot read {file_path!r}: {exc}"
                raise Fail(msg) from exc
            if version is not None:
                if not self._is_python_version_spec(version):
                    # A version file can be a symlink to a secret; only name the configured path.
                    msg = f"base_python_file: {file_path!r} does not contain a Python version specifier"
                    raise Fail(msg)
                return [version]
        msg = f"base_python_file: no valid Python version found in {', '.join(repr(f) for f in file_paths)}"
        raise Fail(msg)

    @classmethod
    def _first_version_line(cls, path: Path, file_path: str) -> str | None:
        with path.open(encoding="utf-8-sig") as file_handler:
            max_length: Final[int] = 1024
            while line := file_handler.readline(max_length + 1):
                stripped = line.strip()
                if len(line) > max_length and not line.endswith("\n"):
                    cls._skip_overlong_line(file_handler, stripped, file_path, max_length)
                    continue
                if stripped and not stripped.startswith("#"):
                    return stripped
        return None

    @staticmethod
    def _skip_overlong_line(file_handler: TextIOWrapper, stripped: str, file_path: str, max_length: int) -> None:
        msg = f"base_python_file: line in {file_path!r} exceeds {max_length} characters"
        if stripped and not stripped.startswith("#"):
            raise Fail(msg)
        is_comment = stripped.startswith("#")
        while continuation := file_handler.readline(max_length + 1):
            stripped_continuation = continuation.strip()
            if not is_comment and stripped_continuation and not stripped_continuation.startswith("#"):
                raise Fail(msg)
            is_comment = is_comment or stripped_continuation.startswith("#")
            if continuation.endswith("\n"):
                break

    @staticmethod
    def _is_python_version_spec(value: str) -> bool:
        spec: Final[PythonSpec] = PythonSpec.from_string_spec(value)
        if spec.path is not None or spec.major is None:
            return False
        if spec.implementation is None:
            return True
        return spec.implementation.lower() in {
            "python",
            "cpython",
            "pypy",
            "jython",
            "graalpy",
            "rustpython",
            "ironpython",
        }

    @abstractmethod
    def env_site_package_dir(self) -> Path:
        """Return the pure-python site-packages directory (purelib) for this environment.

        Debian derivatives change site-packages to dist-packages, so we look at the last path under prefix.

        :returns: the site-packages directory of the environment

        """
        raise NotImplementedError

    def env_site_package_dir_plat(self) -> Path:
        """Return the platform-specific site-packages directory (platlib) for this environment.

        On most platforms this is the same as purelib, but on some Linux distributions (Fedora, RHEL) platlib uses lib64
        instead of lib. Defaults to purelib so third-party runners don't need to override this.

        :returns: the platform-specific site-packages directory of the environment

        """
        return self.env_site_package_dir()

    @abstractmethod
    def env_bin_dir(self) -> Path:
        """The binary folder within the tox environment.

        :returns: the directory holding the executables of the environment

        """
        raise NotImplementedError

    @abstractmethod
    def env_python(self) -> Path:
        """The python executable within the tox environment.

        :returns: the path to the Python interpreter of the environment

        """
        raise NotImplementedError

    def py_dot_ver(self) -> str:
        """The major and minor version of the base python, with a dot.

        :returns: the version, such as ``3.13``

        """
        return self.base_python.version_dot

    @property
    def base_python(self) -> PythonInfo:
        """Resolve base python.

        :raises Skip: when the environment is skipped for lack of an interpreter
        :raises NoInterpreter: when no matching base interpreter is found

        """
        base_pythons = self.conf.get("base_python", list[str])

        if self._base_python_searched is False:
            self._base_python_searched = True
            self._base_python = self._get_python(base_pythons)
            if self._base_python is not None and self.journal:
                self.journal["python"] = self._get_env_journal_python()

        if self._base_python is None:
            if self.conf["skip_missing_interpreters"]:
                msg = f"could not find python interpreter with spec(s): {', '.join(base_pythons)}"
                raise Skip(msg)
            raise NoInterpreter(base_pythons)

        return self._base_python

    @abstractmethod
    def _get_python(self, base_python: list[str]) -> PythonInfo | None:
        raise NotImplementedError

    def _get_env_journal_python(self) -> dict[str, JsonValue]:
        return {
            "implementation": self.base_python.implementation,
            "version_info": tuple(self.base_python.version_info),
            "version": self.base_python.version,
            "is_64": self.base_python.is_64,
            "sysplatform": self.base_python.platform,
            "extra_version_info": None,
            "free_threaded": self.base_python.free_threaded,
            "debug": self.base_python.debug,
            "machine": self.base_python.machine,
        }

    def py_impl(self) -> str:
        """The implementation of the base python, in lower case.

        :returns: the implementation, such as ``cpython``

        """
        return self.base_python.impl_lower

    def py_free_threaded(self) -> bool:
        """Whether the base python is a free-threaded build.

        :returns: whether it is free-threaded

        """
        return self.base_python.free_threaded

    def py_debug(self) -> bool:
        """Whether the base python is a debug build.

        :returns: whether it is a debug build

        """
        return self.base_python.debug

    @override
    def _default_set_env(self) -> dict[str, str]:
        env = super()._default_set_env()
        hash_seed: int | None = getattr(self.options, "hash_seed", None)
        if hash_seed is not None:
            env["PYTHONHASHSEED"] = str(hash_seed)
        return env

    @override
    def _default_pass_env(self) -> list[str]:
        env = super()._default_pass_env()
        if sys.platform == "win32":  # pragma: win32 cover
            env.extend(
                [
                    "APPDATA",  # Needed for PIP platformsdirs.windows
                    "LOCALAPPDATA",  # Needed for pymanager
                    "PROGRAMDATA",  # needed for discovering the VS compiler
                    "PROGRAMFILES(x86)",  # needed for discovering the VS compiler
                    "PROGRAMFILES",  # needed for discovering the VS compiler
                    "SYSTEMDRIVE",
                    "SYSTEMROOT",  # needed for python's crypto module
                    "COMSPEC",  # needed for distutils cygwin compiler
                    "PROCESSOR_ARCHITECTURE",  # platform.machine()
                    "NUMBER_OF_PROCESSORS",  # multiprocessing.cpu_count()
                ],
            )
        env.extend([
            "PKG_CONFIG",
            "PKG_CONFIG_PATH",
            "PKG_CONFIG_SYSROOT_DIR",
        ])  # used by binary extensions during installation
        env.extend(["REQUESTS_CA_BUNDLE"])
        return env

    @override
    def _setup_env(self) -> None:
        """Setup a virtual python environment."""
        super()._setup_env()
        self.ensure_python_env()
        self._paths = self.prepend_env_var_path()  # now that the environment exist we can add them to the path

    def ensure_python_env(self) -> None:
        """Create the python environment, or recreate it when the base python has changed.

        :raises tox.tox_env.errors.Recreate: when the environment exists, but was created with another base python

        """
        conf = self.python_cache()
        with self.cache.compare(conf, Python.__name__) as (eq, old):
            if old is None:  # does not exist -> create
                self.create_python_env()
            elif eq is False:  # pragma: no branch # exists but changed -> recreate
                raise Recreate(self._diff_msg(conf, old))

    def python_cache(self) -> dict[str, JsonValue]:
        """Get the values that decide whether the python environment has to be recreated.

        :returns: the values that identify the base python

        """
        return {
            "version_info": list(self.base_python.version_info),
        }

    @abstractmethod
    def create_python_env(self) -> None:
        """Create the python environment on disk."""
        raise NotImplementedError

    @staticmethod
    def _diff_msg(conf: dict[str, Any], old: dict[str, Any]) -> str:
        result: list[str] = []
        # other outcome untested
        if added := [f"{k}={v!r}" for k, v in conf.items() if k not in old]:  # pragma: no branch
            result.append(f"added {' | '.join(added)}")
        if removed := [f"{k}={v!r}" for k, v in old.items() if k not in conf]:
            result.append(f"removed {' | '.join(removed)}")
        if changed := [f"{k}={old[k]!r}->{v!r}" for k, v in conf.items() if k in old and v != old[k]]:
            result.append(f"changed {' | '.join(changed)}")
        return f"python {', '.join(result)}"

    @abstractmethod
    def prepend_env_var_path(self) -> list[Path]:
        """Get the directories to prepend to the ``PATH`` of the environment.

        :returns: the directories, first one first

        """
        raise NotImplementedError

    @override
    def _done_with_setup(self) -> None:
        """Called when setup is done."""
        super()._done_with_setup()
        if self.journal or self.options.list_dependencies:
            outcome = self.installer.installed()
            if self.journal:
                self.journal["installed_packages"] = outcome
            if self.options.list_dependencies:
                logging.warning(",".join(outcome))


class NoInterpreter(Fail):
    """could not find interpreter.

    :param base_pythons: the base Python names that were searched for

    """

    def __init__(self, base_pythons: list[str]) -> None:
        self.base_pythons = base_pythons

    @override
    def __str__(self) -> str:
        return f"could not find python interpreter matching any of the specs {', '.join(self.base_pythons)}"


def add_skip_missing_interpreters_to_core(core: CoreConfigSet, options: Parsed) -> None:
    """Add the ``skip_missing_interpreters`` setting to the core configuration.

    :param core: the core configuration
    :param options: the parsed command line options

    """
    core.add_config(
        keys=["skip_missing_interpreters"],
        default=False,
        of_type=bool,
        post_process=partial(_skip_missing_interpreters_post_process, options),
        desc="skip running missing interpreters",
    )


# option parser fixes the callback signature
def _skip_missing_interpreters_post_process(options: Parsed, value: bool) -> bool:  # ruff:ignore[boolean-type-hint-positional-argument]
    if getattr(options, "skip_missing_interpreters", "config") != "config":
        return StrConvert().to_bool(str(options.skip_missing_interpreters))
    return value


def add_skip_missing_interpreters_to_env(conf: EnvConfigSet, core: CoreConfigSet, options: Parsed) -> None:
    """Add the ``skip_missing_interpreters`` setting to the configuration of an environment.

    :param conf: the configuration of the environment
    :param core: the core configuration
    :param options: the parsed command line options

    """

    def _default_skip_missing(  # interface signature
        conf: Config,  # ruff:ignore[unused-function-argument]  # interface signature
        env_name: str | None,  # ruff:ignore[unused-function-argument]  # interface signature
    ) -> bool:
        return core.get("skip_missing_interpreters", bool)

    conf.add_config(
        keys=["skip_missing_interpreters"],
        default=_default_skip_missing,
        of_type=bool,
        post_process=partial(_skip_missing_interpreters_post_process, options),
        desc="override core skip_missing_interpreters for this environment",
    )


__all__ = [
    "NoInterpreter",
    "Python",
    "PythonInfo",
    "VersionInfo",
    "add_skip_missing_interpreters_to_core",
    "add_skip_missing_interpreters_to_env",
]
