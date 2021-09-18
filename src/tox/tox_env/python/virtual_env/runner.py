"""
A tox python environment runner that uses the virtualenv project.
"""
from pathlib import Path

from tox.plugin import impl
from tox.tox_env.register import ToxEnvRegister

from ..runner import PythonRun
from .api import VirtualEnv


class VirtualEnvRunner(VirtualEnv, PythonRun):
    """local file system python virtual environment via the virtualenv package"""

    @staticmethod
    def id() -> str:
        return "virtualenv"

    @property
    def _default_package_tox_env_type(self) -> str:
        return "virtualenv-pep-517"

    @property
    def has_package_by_default(self) -> bool:
        tox_root: Path = self.core["tox_root"]
        return (
            getattr(self.options, "install_pkg", None) is not None
            or (tox_root / "pyproject.toml").exists()
            or (tox_root / "setup.py").exists()
        )


@impl
def tox_register_tox_env(register: ToxEnvRegister) -> None:
    register.add_run_env(VirtualEnvRunner)
