from typing import Any, Dict

from tox.plugin.impl import impl
from tox.tox_env.register import ToxEnvRegister

from .api import Pep517VirtualEnvPackageArtifact


class Pep517VirtualEnvPackageWheel(Pep517VirtualEnvPackageArtifact):
    @property
    def build_type(self) -> str:
        return "wheel"

    @property
    def extra(self) -> Dict[str, Any]:
        return {
            "config_settings": {
                "--global-option": ["--bdist-dir", str(self.conf["env_dir"] / "build")]
            },
            "metadata_directory": str(self.meta_folder) if self.meta_folder.exists() else None,
        }

    @staticmethod
    def id() -> str:
        return "virtualenv-pep-517-wheel"


@impl
def tox_register_tox_env(register: ToxEnvRegister) -> None:
    register.add_package_env(Pep517VirtualEnvPackageWheel)
