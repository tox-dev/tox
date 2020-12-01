from pathlib import Path
from typing import Tuple

from packaging.requirements import Requirement

from tox.plugin.impl import impl
from tox.tox_env.register import ToxEnvRegister

from ..api import Pep517VirtualEnvPackage


class Pep517VirtualEnvPackageSdist(Pep517VirtualEnvPackage):
    @staticmethod
    def id() -> str:
        return "virtualenv-pep-517-sdist"

    def build_requires(self) -> Tuple[Requirement, ...]:
        result = self.get_requires_for_build_sdist()
        return result.requires

    def _build_artifact(self) -> Path:
        result = self.build_sdist(sdist_directory=self.pkg_dir)
        return result.sdist


@impl
def tox_register_tox_env(register: ToxEnvRegister) -> None:
    register.add_package_env(Pep517VirtualEnvPackageSdist)
