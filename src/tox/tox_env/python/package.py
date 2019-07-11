import sys
from abc import ABC, abstractmethod
from typing import List

from packaging.requirements import Requirement

from ..package import PackageToxEnv
from .api import Python


class PythonPackage(Python, PackageToxEnv, ABC):
    def setup(self) -> None:
        """setup the tox environment"""
        super().setup()
        self.cached_install(self.requires(), PythonPackage.__name__, "requires")
        self.cached_install(self.build_requires(), PythonPackage.__name__, "build-requires")

    @abstractmethod
    def requires(self) -> List[Requirement]:
        raise NotImplementedError

    @abstractmethod
    def build_requires(self) -> List[Requirement]:
        raise NotImplementedError

    def default_base_python(self) -> List[str]:
        return [sys.executable]
