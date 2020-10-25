"""
Declare the abstract base class for tox environments that handle the Python language.
"""
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    NamedTuple,
    NoReturn,
    Optional,
    Sequence,
    Union,
    cast,
)

from packaging.requirements import Requirement
from virtualenv.discovery.py_spec import PythonSpec

from tox.config.cli.parser import Parsed
from tox.config.main import Config
from tox.config.sets import ConfigSet
from tox.tox_env.api import ToxEnv
from tox.tox_env.errors import Fail, Recreate


class VersionInfo(NamedTuple):
    major: int
    minor: int
    micro: int
    releaselevel: str
    serial: int


class PythonInfo(NamedTuple):
    version_info: VersionInfo
    executable: Path


Deps = Sequence[Union[Path, Requirement]]


class Python(ToxEnv, ABC):
    def __init__(self, conf: ConfigSet, core: ConfigSet, options: Parsed) -> None:
        self._base_python: Optional[PythonInfo] = None
        self._base_python_searched: bool = False
        super(Python, self).__init__(conf, core, options)

    def register_config(self) -> None:
        super().register_config()
        self.conf.add_config(
            keys=["base_python", "basepython"],
            of_type=List[str],
            default=self.default_base_python,
            desc="environment identifier for python, first one found wins",
        )
        self.conf.add_constant(
            keys=["env_site_packages_dir", "envsitepackagesdir"],
            desc="the python environments site package",
            value=lambda: self.env_site_package_dir(),
        )

    def default_pass_env(self) -> List[str]:
        env = super().default_pass_env()
        if sys.platform == "win32":
            env.extend(
                [
                    "SYSTEMROOT",  # needed for python's crypto module
                    "PATHEXT",  # needed for discovering executables
                    "COMSPEC",  # needed for distutils cygwin compiler
                    "PROCESSOR_ARCHITECTURE",  # platform.machine()
                    "USERPROFILE",  # needed for `os.path.expanduser()`
                    "MSYSTEM",  # controls paths printed format
                ]
            )
        return env

    def default_base_python(self, conf: "Config", env_name: Optional[str]) -> List[str]:
        spec = PythonSpec.from_string_spec(env_name)
        if spec.implementation is not None:
            if spec.implementation.lower() in ("cpython", "pypy") and env_name is not None:
                return [env_name]
        return [sys.executable]

    @abstractmethod
    def env_site_package_dir(self) -> Path:
        """
        If we have the python we just need to look at the last path under prefix.
        E.g., Debian derivatives change the site-packages to dist-packages, so we need to fix it for site-packages.
        """
        raise NotImplementedError

    def setup(self) -> None:
        """setup a virtual python environment"""
        super().setup()
        conf = self.python_cache()
        with self._cache.compare(conf, Python.__name__) as (eq, old):
            if eq is False:
                self.create_python_env()
            self._paths = self.paths()

    def python_cache(self) -> Dict[str, Any]:
        return {
            "version_info": list(self.base_python.version_info),
            "executable": self.base_python.executable,
        }

    @property
    def base_python(self) -> PythonInfo:
        """Resolve base python"""
        if self._base_python_searched is False:
            base_pythons = self.conf["base_python"]
            self._base_python_searched = True
            self._base_python = self._get_python(base_pythons)
            if self._base_python is None:
                self.no_base_python_found(base_pythons)
        return cast(PythonInfo, self._base_python)

    @abstractmethod
    def no_base_python_found(self, base_pythons: List[str]) -> NoReturn:
        raise NotImplementedError

    @abstractmethod
    def _get_python(self, base_python: List[str]) -> Optional[PythonInfo]:
        raise NotImplementedError

    def cached_install(self, deps: Deps, section: str, of_type: str) -> bool:
        conf_deps = [str(i) for i in deps]
        with self._cache.compare(conf_deps, section, of_type) as (eq, old):
            if eq is True:
                return True
            if old is None:
                old = []
            missing = [Requirement(i) for i in (set(old) - set(conf_deps))]
            if missing:  # no way yet to know what to uninstall here (transitive dependencies?)
                # bail out and force recreate
                raise Recreate()
            new_deps_str = set(conf_deps) - set(old)
            new_deps = [Requirement(i) for i in new_deps_str]
            self.install_python_packages(packages=new_deps)
        return False

    @abstractmethod
    def create_python_env(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def paths(self) -> List[Path]:
        raise NotImplementedError

    @abstractmethod
    def install_python_packages(self, packages: Deps, no_deps: bool = False) -> None:
        raise NotImplementedError


class NoInterpreter(Fail):
    """could not find interpreter"""

    def __init__(self, base_pythons: List[str]) -> None:
        self.python = base_pythons
