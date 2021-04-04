"""
A tox build environment that handles Python packages.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Sequence, Tuple

from packaging.requirements import Requirement

from ..package import Package, PackageToxEnv, PathPackage
from .api import Python


class PythonPackage(Package):
    """python package"""


class PythonPathPackageWithDeps(PathPackage):
    def __init__(self, path: Path, deps: Sequence[Any]) -> None:
        super().__init__(path=path)
        self.deps: Sequence[Package] = deps


class WheelPackage(PythonPathPackageWithDeps):
    """wheel package"""


class SdistPackage(PythonPathPackageWithDeps):
    """sdist package"""


class DevLegacyPackage(PythonPathPackageWithDeps):
    """legacy dev package"""


class PythonPackageToxEnv(Python, PackageToxEnv, ABC):
    def register_config(self) -> None:
        super().register_config()

    def _setup_env(self) -> None:
        """setup the tox environment"""
        super()._setup_env()
        self.installer.install(self.requires(), PythonPackageToxEnv.__name__, "requires")

    @abstractmethod
    def requires(self) -> Tuple[Requirement, ...]:
        raise NotImplementedError
