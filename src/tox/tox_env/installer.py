from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Generic, TypeAlias

from packaging.requirements import Requirement

from .api import ToxEnv
from .package import Package
from .python.pip.req_file import PythonDeps
from .python.pylock import Pylock

if sys.version_info >= (3, 13):  # pragma: >=3.13 cover
    from typing import TypeVar
else:  # pragma: <3.13 cover
    from typing_extensions import TypeVar

InstallArguments: TypeAlias = PythonDeps | Pylock | Sequence[Requirement | Package]
"""Argument types tox itself passes to :meth:`Installer.install` and the ``tox_on_install`` hook."""

EnvT_co = TypeVar("EnvT_co", bound=ToxEnv, covariant=True)
ArgsT = TypeVar("ArgsT", default=InstallArguments)


class Installer(ABC, Generic[EnvT_co, ArgsT]):
    """Install packages into a tox environment; ``ArgsT`` is what :meth:`install` accepts.

    :param tox_env: the environment to install the packages into

    """

    def __init__(self, tox_env: EnvT_co) -> None:
        self._env = tox_env
        self._register_config()

    @abstractmethod
    def _register_config(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def installed(self) -> list[str]:
        """:returns: a list of packages installed (JSON dump-able)"""
        raise NotImplementedError

    @abstractmethod
    def install(self, arguments: ArgsT, section: str, of_type: str) -> None:
        raise NotImplementedError


__all__ = [
    "InstallArguments",
    "Installer",
]
