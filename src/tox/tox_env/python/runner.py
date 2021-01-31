"""
A tox run environment that handles the Python language.
"""
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, cast

from tox.config.cli.parser import Parsed
from tox.config.sets import CoreConfigSet, EnvConfigSet
from tox.journal import EnvJournal
from tox.report import ToxHandler
from tox.tox_env.errors import Recreate
from tox.tox_env.package import PackageToxEnv

from ..runner import RunToxEnv
from .api import Python, PythonDep
from .req_file import RequirementsFile


class PythonRun(Python, RunToxEnv, ABC):
    def __init__(
        self, conf: EnvConfigSet, core: CoreConfigSet, options: Parsed, journal: EnvJournal, log_handler: ToxHandler
    ):
        super().__init__(conf, core, options, journal, log_handler)
        self._packages: List[PythonDep] = []

    def register_config(self) -> None:
        super().register_config()
        deps_kwargs = {"root": self.core["toxinidir"]}
        self.conf.add_config(
            keys="deps",
            of_type=RequirementsFile,
            kwargs=deps_kwargs,
            default=RequirementsFile("", **deps_kwargs),
            desc="Name of the python dependencies as specified by PEP-440",
        )
        self.core.add_config(
            keys=["skip_missing_interpreters"],
            default=True,
            of_type=bool,
            desc="skip running missing interpreters",
        )

    def before_package_install(self) -> None:
        super().before_package_install()
        # install deps
        requirements_file: RequirementsFile = self.conf["deps"]
        requirement_file_content = requirements_file.validate_and_expand()
        requirement_file_content.sort()  # stable order dependencies
        with self._cache.compare(requirement_file_content, PythonRun.__name__, "deps") as (eq, old):
            if not eq:
                # if new env, or additions only a simple install will do
                missing: Set[str] = set() if old is None else set(old) - set(requirement_file_content)
                if not missing:
                    if requirement_file_content:
                        with requirements_file.with_file() as path:
                            self.install_requirement_file(path)
                else:  # otherwise, no idea how to compute the diff, instead just start from scratch
                    logging.warning(f"recreate env because dependencies removed: {', '.join(str(i) for i in missing)}")
                    raise Recreate

    def install_package(self) -> List[Path]:
        package_env = cast(PackageToxEnv, self.package_env)
        explicit_install_package: Optional[Path] = getattr(self.options, "install_pkg", None)
        if explicit_install_package is None:
            # 1. install package dependencies
            with package_env.display_context(suspend=self.has_display_suspended):
                package_deps = package_env.get_package_dependencies(self.conf)
            self.cached_install([PythonDep(p) for p in package_deps], PythonRun.__name__, "package_deps")

            # 2. install the package
            with package_env.display_context(suspend=self.has_display_suspended):
                self._packages = [PythonDep(p) for p in package_env.perform_packaging(self.conf.name)]
        else:
            # ideally here we should parse the package dependencies, but that would break tox 3 behaviour
            # and might not be trivial (e.g. in case of sdist), for now keep legacy functionality
            self._packages = [PythonDep(explicit_install_package)]
        self.install_python_packages(
            self._packages, "package", **self.install_package_args()  # type: ignore[no-untyped-call]
        )
        return [i.value for i in self._packages if isinstance(i.value, Path)]

    @abstractmethod
    def install_package_args(self) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def install_requirement_file(self, path: Path) -> None:
        raise NotImplementedError

    @property
    def packages(self) -> List[str]:
        return [str(d.value) for d in self._packages]
