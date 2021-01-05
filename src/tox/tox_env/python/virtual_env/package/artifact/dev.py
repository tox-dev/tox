from pathlib import Path
from typing import List, Set, Tuple, cast

from packaging.requirements import Requirement

from tox.plugin.impl import impl
from tox.tox_env.register import ToxEnvRegister

from ..api import Pep517VirtualEnvPackage


class LegacyDevVirtualEnvPackage(Pep517VirtualEnvPackage):
    """Use PEP-517 to get package build and runtime dependencies - install the root folder"""

    def _build_artifact(self) -> Path:
        return cast(Path, self.core["tox_root"])  # the folder itself is the package

    def get_package_dependencies(self, extras: Set[str]) -> List[Requirement]:
        # install build-requires dependencies so that the legacy installer has them satisfied when installing package
        result = super().get_package_dependencies(extras)
        result.extend(self.build_requires())
        return result

    @staticmethod
    def id() -> str:
        return "virtualenv-legacy-dev"

    def build_requires(self) -> Tuple[Requirement, ...]:
        result: Tuple[Requirement, ...] = ()
        return result


@impl
def tox_register_tox_env(register: ToxEnvRegister) -> None:
    register.add_package_env(LegacyDevVirtualEnvPackage)
