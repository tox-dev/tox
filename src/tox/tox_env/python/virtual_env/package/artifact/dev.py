from pathlib import Path
from typing import Tuple, cast

from packaging.requirements import Requirement

from tox.plugin.impl import impl
from tox.tox_env.python.api import PythonDep, PythonDeps
from tox.tox_env.register import ToxEnvRegister

from ..api import Pep517VirtualEnvPackage


class LegacyDevVirtualEnvPackage(Pep517VirtualEnvPackage):
    """Use PEP-517 to get package build and runtime dependencies - install the root folder"""

    def _build_artifact(self) -> Path:
        return cast(Path, self.core["tox_root"])  # the folder itself is the package

    @staticmethod
    def id() -> str:
        return "virtualenv-legacy-dev"

    def build_requires(self) -> Tuple[Requirement, ...]:
        result: Tuple[Requirement, ...] = ()
        return result

    def package_deps(self) -> PythonDeps:
        """Install requirement from pyproject.toml table"""
        return [PythonDep(i) for i in self._requires]


@impl
def tox_register_tox_env(register: ToxEnvRegister) -> None:
    register.add_package_env(LegacyDevVirtualEnvPackage)
