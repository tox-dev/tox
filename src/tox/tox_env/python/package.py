"""
A tox build environment that handles Python packages.
"""
from abc import ABC, abstractmethod
from typing import Tuple

from packaging.requirements import Requirement

from ..package import PackageToxEnv
from .api import Python, PythonDep


class PythonPackage(Python, PackageToxEnv, ABC):
    def setup(self) -> None:
        """setup the tox environment"""
        super().setup()

        requires = [PythonDep(i) for i in self.requires()]
        self.cached_install(requires, PythonPackage.__name__, "requires")

    @abstractmethod
    def requires(self) -> Tuple[Requirement, ...]:
        raise NotImplementedError
