"""Concrete virtualenv-backed PEP 723 runner."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tox.plugin import impl
from tox.tox_env.python.pep723 import Pep723Mixin
from tox.tox_env.runner import RunToxEnv

from .api import VirtualEnv

if TYPE_CHECKING:
    from tox.tox_env.package import Package
    from tox.tox_env.register import ToxEnvRegister


class Pep723Runner(Pep723Mixin, VirtualEnv, RunToxEnv):
    @staticmethod
    def id() -> str:
        return "virtualenv-pep-723"

    def _register_package_conf(self) -> bool:  # noqa: PLR6301
        return False

    @property
    def _package_tox_env_type(self) -> str:
        raise NotImplementedError

    @property
    def _external_pkg_tox_env_type(self) -> str:
        raise NotImplementedError

    def _build_packages(self) -> list[Package]:  # noqa: PLR6301
        return []


@impl
def tox_register_tox_env(register: ToxEnvRegister) -> None:
    register.add_run_env(Pep723Runner)


__all__ = [
    "Pep723Runner",
]
