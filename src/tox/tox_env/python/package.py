"""
A tox build environment that handles Python packages.
"""
import sys
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Union

from packaging.requirements import Requirement

from tox.config.main import Config

from ..package import PackageToxEnv
from .api import Python, PythonDep


class PythonPackage(Python, PackageToxEnv, ABC):
    def setup(self) -> None:
        """setup the tox environment"""
        super().setup()
        deps = [PythonDep(i) for i in self.requires()]
        if not self.cached_install(deps, PythonPackage.__name__, "requires"):
            build_requirements: List[Union[str, Requirement]] = []
            with self._cache.compare(build_requirements, PythonPackage.__name__, "build-requires") as (eq, old):
                if eq is False and old is None:
                    build_requires = self.build_requires()
                    build_requirements.extend(str(i) for i in build_requires)
                    self.install_python_packages(packages=[PythonDep(i) for i in build_requires])

    @abstractmethod
    def requires(self) -> Tuple[Requirement, ...]:
        raise NotImplementedError

    @abstractmethod
    def build_requires(self) -> Tuple[Requirement, ...]:
        raise NotImplementedError

    def default_base_python(self, conf: Config, env_name: Optional[str]) -> List[str]:
        return [sys.executable]
