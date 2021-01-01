"""
A tox build environment that handles Python packages.
"""
import sys
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from packaging.requirements import Requirement

from tox.config.main import Config

from ..package import PackageToxEnv
from .api import Python, PythonDep


class PythonPackage(Python, PackageToxEnv, ABC):
    def setup(self) -> None:
        """setup the tox environment"""
        super().setup()

        requires = [PythonDep(i) for i in self.requires()]
        self.cached_install(requires, PythonPackage.__name__, "requires")

        build_requires = [PythonDep(i) for i in self.build_requires()]
        self.cached_install(build_requires, PythonPackage.__name__, "build-requires")

    @abstractmethod
    def requires(self) -> Tuple[Requirement, ...]:
        raise NotImplementedError

    @abstractmethod
    def build_requires(self) -> Tuple[Requirement, ...]:
        raise NotImplementedError

    def default_base_python(self, conf: Config, env_name: Optional[str]) -> List[str]:
        return [sys.executable]
