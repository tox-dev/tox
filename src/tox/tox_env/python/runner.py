"""
A tox run environment that handles the Python language.
"""
import logging
from abc import ABC, abstractmethod
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List, Set

from tox.config.cli.parser import Parsed
from tox.config.sets import CoreConfigSet, EnvConfigSet
from tox.journal import EnvJournal
from tox.report import ToxHandler
from tox.tox_env.errors import Recreate

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
        self.conf.add_config(
            keys="deps",
            of_type=RequirementsFile,
            default=RequirementsFile(""),
            desc="Name of the python dependencies as specified by PEP-440",
        )
        self.core.add_config(
            keys=["skip_missing_interpreters"],
            default=True,
            of_type=bool,
            desc="skip running missing interpreters",
        )

    def setup(self) -> None:
        """setup the tox environment"""
        super().setup()
        self.install_deps()

        if self.package_env is None:
            return
        skip_pkg_install: bool = getattr(self.options, "skip_pkg_install", False)
        if skip_pkg_install is True:
            logging.warning("skip building and installing the package")
            return

        # 1. install pkg dependencies
        with self.package_env.display_context(suspend=self.has_display_suspended):
            package_deps = self.package_env.get_package_dependencies(self.conf)
        self.cached_install([PythonDep(p) for p in package_deps], PythonRun.__name__, "package_deps")

        # 2. install the package
        with self.package_env.display_context(suspend=self.has_display_suspended):
            self._packages = [PythonDep(p) for p in self.package_env.perform_packaging(self.conf.name)]
        self.install_python_packages(
            self._packages, "package", **self.install_package_args()  # type: ignore[no-untyped-call]
        )
        self.handle_journal_package(self.journal, self._packages)

    def install_deps(self) -> None:
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

    @abstractmethod
    def install_package_args(self) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def install_requirement_file(self, path: Path) -> None:
        raise NotImplementedError

    @property
    def packages(self) -> List[str]:
        return [str(d.value) for d in self._packages]

    @staticmethod
    def handle_journal_package(journal: EnvJournal, package: List[PythonDep]) -> None:
        if not journal:
            return
        installed_meta = []
        for dep in package:
            if isinstance(dep.value, Path):
                pkg = dep.value
                of_type = "file" if pkg.is_file() else ("dir" if pkg.is_dir() else "N/A")
                meta = {"basename": pkg.name, "type": of_type}
                if of_type == "file":
                    meta["sha256"] = sha256(pkg.read_bytes()).hexdigest()
                installed_meta.append(meta)
        if installed_meta:
            journal["installpkg"] = installed_meta[0] if len(installed_meta) == 1 else installed_meta
