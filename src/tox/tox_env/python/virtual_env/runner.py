"""A tox python environment runner that uses the virtualenv project."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from tox.plugin import impl
from tox.tox_env.python.runner import PythonRun
from tox.util.typing_compat import override

from .api import VirtualEnv

if TYPE_CHECKING:
    from tox.tox_env.register import ToxEnvRegister


class VirtualEnvRunner(VirtualEnv, PythonRun):
    """local file system python virtual environment via the virtualenv package."""

    @staticmethod
    @override
    def id() -> str:
        return "virtualenv"

    @property
    @override
    def _package_tox_env_type(self) -> str:
        return "virtualenv-pep-517"

    @property
    @override
    def _external_pkg_tox_env_type(self) -> str:
        return "virtualenv-cmd-builder"

    @property
    @override
    def default_pkg_type(self) -> str:
        tox_root = self.core.get("tox_root", Path)
        if not (any((tox_root / i).exists() for i in ("pyproject.toml", "setup.py", "setup.cfg"))):
            return "skip"
        return super().default_pkg_type


@impl
def tox_register_tox_env(register: ToxEnvRegister) -> None:
    register.add_run_env(VirtualEnvRunner)
