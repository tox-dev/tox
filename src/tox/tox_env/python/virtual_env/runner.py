"""A tox python environment runner that uses the virtualenv project."""

from __future__ import annotations

__lazy_modules__ = ["pathlib"]

from pathlib import Path
from typing import TYPE_CHECKING

from tox.plugin import impl
from tox.tox_env.python.runner import PythonRun
from tox.util.typing_compat import override

from .api import VirtualEnv

if TYPE_CHECKING:
    from tox.tox_env.register import ToxEnvRegister


@impl
def tox_register_tox_env(register: ToxEnvRegister) -> None:
    """Register the virtualenv run environment with tox.

    :param register: the registry of environment types

    """
    register.add_run_env(VirtualEnvRunner)


class VirtualEnvRunner(VirtualEnv, PythonRun):
    """local file system python virtual environment via the virtualenv package."""

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
        build_files = ("pyproject.toml", "setup.py", "setup.cfg")
        if any((tox_root / filename).exists() for filename in build_files):
            return super().default_pkg_type
        package_root = self.core.package_root_for_discovery()
        if (
            package_root is not None
            and package_root != tox_root
            and any((package_root / filename).exists() for filename in build_files)
        ):
            return super().default_pkg_type
        return "skip"

    @staticmethod
    @override
    def id() -> str:
        return "virtualenv"
