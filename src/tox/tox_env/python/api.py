"""
Declare the abstract base class for tox environments that handle the Python language.
"""
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, cast

from packaging.tags import INTERPRETER_SHORT_NAMES
from virtualenv.discovery.py_spec import PythonSpec

from tox.config.main import Config
from tox.tox_env.api import ToxEnv, ToxEnvCreateArgs
from tox.tox_env.errors import Fail, Recreate, Skip


class VersionInfo(NamedTuple):
    major: int
    minor: int
    micro: int
    releaselevel: str
    serial: int


class PythonInfo(NamedTuple):
    implementation: str
    version_info: VersionInfo
    version: str
    is_64: bool
    platform: str
    extra: Dict[str, Any]

    @property
    def version_no_dot(self) -> str:
        return f"{self.version_info.major}{self.version_info.minor}"

    @property
    def impl_lower(self) -> str:
        return self.implementation.lower()


class Python(ToxEnv, ABC):
    def __init__(self, create_args: ToxEnvCreateArgs) -> None:
        self._base_python: Optional[PythonInfo] = None
        self._base_python_searched: bool = False
        super().__init__(create_args)

    def register_config(self) -> None:
        super().register_config()

        def validate_base_python(value: List[str]) -> List[str]:
            return self._validate_base_python(self.name, value, self.core["ignore_base_python_conflict"])

        self.conf.add_config(
            keys=["base_python", "basepython"],
            of_type=List[str],
            default=self.default_base_python,
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
            desc="the python environments site package",
            value=lambda: self.env_site_package_dir(),
        )
        self.conf.add_constant(
            keys=["env_bin_dir", "envbindir"],
            desc="the python environments binary folder",
            value=lambda: self.env_bin_dir(),
        )
        self.conf.add_constant(
            ["env_python", "envpython"],
            desc="python executable from within the tox environment",
            value=lambda: self.env_python(),
        )

    def _default_pass_env(self) -> List[str]:
        env = super()._default_pass_env()
        if sys.platform == "win32":  # pragma: win32 cover
            env.extend(
                [
                    "SYSTEMDRIVE",
                    "SYSTEMROOT",  # needed for python's crypto module
                    "COMSPEC",  # needed for distutils cygwin compiler
                    "PROCESSOR_ARCHITECTURE",  # platform.machine()
                ]
            )
        env.extend(["REQUESTS_CA_BUNDLE"])
        return env

    def default_base_python(self, conf: "Config", env_name: Optional[str]) -> List[str]:  # noqa: U100
        base_python = None if env_name is None else self.extract_base_python(env_name)
        return [sys.executable if base_python is None else base_python]

    @staticmethod
    def extract_base_python(env_name: str) -> Optional[str]:
        candidates: List[str] = []
        for factor in env_name.split("-"):
            spec = PythonSpec.from_string_spec(factor)
            if spec.implementation is not None:
                if spec.implementation.lower() in INTERPRETER_SHORT_NAMES and env_name is not None:
                    candidates.append(factor)
        if candidates:
            if len(candidates) > 1:
                raise ValueError(f"conflicting factors {', '.join(candidates)} in {env_name}")
            return next(iter(candidates))
        return None

    @staticmethod
    def _validate_base_python(env_name: str, base_pythons: List[str], ignore_base_python_conflict: bool) -> List[str]:
        elements = {env_name}  # match with full env-name
        elements.update(env_name.split("-"))  # and also any factor
        for candidate in elements:
            spec_name = PythonSpec.from_string_spec(candidate)
            if spec_name.implementation is not None and spec_name.implementation.lower() in ("pypy", "cpython"):
                for base_python in base_pythons:
                    spec_base = PythonSpec.from_string_spec(base_python)
                    if any(
                        getattr(spec_base, key) != getattr(spec_name, key)
                        for key in ("implementation", "major", "minor", "micro", "architecture")
                        if getattr(spec_base, key) is not None and getattr(spec_name, key) is not None
                    ):
                        msg = f"env name {env_name} conflicting with base python {base_python}"
                        if ignore_base_python_conflict:
                            return [env_name]  # ignore the base python settings
                        raise Fail(msg)
        return base_pythons

    @abstractmethod
    def env_site_package_dir(self) -> Path:
        """
        If we have the python we just need to look at the last path under prefix.
        E.g., Debian derivatives change the site-packages to dist-packages, so we need to fix it for site-packages.
        """
        raise NotImplementedError

    @abstractmethod
    def env_python(self) -> Path:
        """The python executable within the tox environment"""
        raise NotImplementedError

    @abstractmethod
    def env_bin_dir(self) -> Path:
        """The binary folder within the tox environment"""
        raise NotImplementedError

    def _setup_env(self) -> None:
        """setup a virtual python environment"""
        super()._setup_env()
        self.ensure_python_env()
        self._paths = self.prepend_env_var_path()  # now that the environment exist we can add them to the path

    def ensure_python_env(self) -> None:
        conf = self.python_cache()
        with self.cache.compare(conf, Python.__name__) as (eq, old):
            if old is None:  # does not exist -> create
                self.create_python_env()
            elif eq is False:  # pragma: no branch # exists but changed -> recreate
                raise Recreate(self._diff_msg(conf, old))

    @staticmethod
    def _diff_msg(conf: Dict[str, Any], old: Dict[str, Any]) -> str:
        result: List[str] = []
        added = [f"{k}={v!r}" for k, v in conf.items() if k not in old]
        if added:  # pragma: no branch
            result.append(f"added {' | '.join(added)}")
        removed = [f"{k}={v!r}" for k, v in old.items() if k not in conf]
        if removed:
            result.append(f"removed {' | '.join(removed)}")
        changed = [f"{k}={old[k]!r}->{v!r}" for k, v in conf.items() if k in old and v != old[k]]
        if changed:
            result.append(f"changed {' | '.join(changed)}")
        return f'python {", ".join(result)}'

    @abstractmethod
    def prepend_env_var_path(self) -> List[Path]:
        raise NotImplementedError

    def _done_with_setup(self) -> None:
        """called when setup is done"""
        super()._done_with_setup()
        if self.journal:
            outcome = self.installer.installed()
            self.journal["installed_packages"] = outcome

    def python_cache(self) -> Dict[str, Any]:
        return {
            "version_info": list(self.base_python.version_info),
        }

    @property
    def base_python(self) -> PythonInfo:
        """Resolve base python"""
        if self._base_python_searched is False:
            base_pythons: List[str] = self.conf["base_python"]
            self._base_python_searched = True
            self._base_python = self._get_python(base_pythons)
            if self._base_python is None:
                if self.core["skip_missing_interpreters"]:
                    raise Skip(f"could not find python interpreter with spec(s): {', '.join(base_pythons)}")
                raise NoInterpreter(base_pythons)
            if self.journal:
                value = self._get_env_journal_python()
                self.journal["python"] = value
        return cast(PythonInfo, self._base_python)

    def _get_env_journal_python(self) -> Dict[str, Any]:
        assert self._base_python is not None
        return {
            "implementation": self._base_python.implementation,
            "version_info": tuple(self.base_python.version_info),
            "version": self._base_python.version,
            "is_64": self._base_python.is_64,
            "sysplatform": self._base_python.platform,
            "extra_version_info": None,
        }

    @abstractmethod
    def _get_python(self, base_python: List[str]) -> Optional[PythonInfo]:
        raise NotImplementedError

    @abstractmethod
    def create_python_env(self) -> None:
        raise NotImplementedError


class NoInterpreter(Fail):
    """could not find interpreter"""

    def __init__(self, base_pythons: List[str]) -> None:
        self.base_pythons = base_pythons

    def __str__(self) -> str:
        return f"could not find python interpreter matching any of the specs {', '.join(self.base_pythons)}"
