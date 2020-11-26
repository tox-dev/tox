"""
A tox run environment that handles the Python language.
"""
from abc import ABC, abstractmethod
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List, NoReturn, Union, cast

from packaging.requirements import Requirement

from tox.config.cli.parser import Parsed
from tox.config.sets import ConfigSet
from tox.journal import EnvJournal
from tox.tox_env.errors import Skip

from ..runner import RunToxEnv
from .api import NoInterpreter, Python, PythonDep


class PythonRun(Python, RunToxEnv, ABC):
    def __init__(self, conf: ConfigSet, core: ConfigSet, options: Parsed, journal: EnvJournal):
        super().__init__(conf, core, options, journal)
        self._packages: List[PythonDep] = []

    def register_config(self) -> None:
        super().register_config()
        outer_self = self

        class _PythonDep(PythonDep):
            def __init__(self, raw: Union[PythonDep, str]) -> None:
                if isinstance(raw, str):
                    if raw.startswith("-r"):
                        val: Union[Path, Requirement] = Path(raw[2:])
                        if not cast(Path, val).is_absolute():
                            val = outer_self.core["toxinidir"] / val
                    else:
                        val = Requirement(raw)
                else:
                    val = raw.value
                super().__init__(val)

        self.conf.add_config(
            keys="deps",
            of_type=List[_PythonDep],
            default=[],
            desc="Name of the python dependencies as specified by PEP-440",
        )
        self.core.add_config(
            keys=["skip_missing_interpreters"],
            default=True,
            of_type=bool,
            desc="skip running missing interpreters",
        )

    def no_base_python_found(self, base_pythons: List[str]) -> NoReturn:
        if self.core["skip_missing_interpreters"]:
            raise Skip
        raise NoInterpreter(base_pythons)

    def setup(self) -> None:
        """setup the tox environment"""
        super().setup()
        self.install_deps()
        if self.package_env is not None:
            package_deps = self.package_env.get_package_dependencies(self.conf["extras"])
            self.cached_install([PythonDep(p) for p in package_deps], PythonRun.__name__, "package_deps")
        self.install_package()

    def install_deps(self) -> None:
        self.cached_install(self.conf["deps"], PythonRun.__name__, "deps")

    def install_package(self) -> None:
        package = self.get_package()
        if package:
            self.install_python_packages(package, **self.install_package_args())  # type: ignore[no-untyped-call]
            self.handle_journal_package(self.journal, package)

    def get_package(self) -> List[PythonDep]:
        if self.package_env is not None:
            package: List[PythonDep] = [PythonDep(p) for p in self.package_env.perform_packaging()]
        else:
            package = [PythonDep(d) for d in self.get_pkg_no_env()] if self.has_package else []
        self._packages = package
        return package

    @abstractmethod
    def install_package_args(self) -> Dict[str, Any]:
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

    def get_pkg_no_env(self) -> List[Path]:
        # by default in Python just forward the root folder to the installer
        return [cast(Path, self.core["tox_root"])]
