"""
A tox build environment that handles Python packages.
"""
import sys
from abc import ABC, abstractmethod
from typing import List, NoReturn, Optional, Union

from packaging.requirements import Requirement

from tox.config.main import Config

from ..package import PackageToxEnv
from .api import NoInterpreter, Python, PythonDep


class PythonPackage(Python, PackageToxEnv, ABC):
    def setup(self) -> None:
        """setup the tox environment"""
        super().setup()
        fresh_requires = self.cached_install(
            [PythonDep(i) for i in self.requires()], PythonPackage.__name__, "requires"
        )
        if not fresh_requires:
            build_requirements: List[Union[str, Requirement]] = []
            with self._cache.compare(build_requirements, PythonPackage.__name__, "build-requires") as (eq, old):
                if eq is False and old is None:
                    build_requirements.extend(self.build_requires())
                    new_deps = [PythonDep(Requirement(i) if isinstance(i, str) else i) for i in set(build_requirements)]
                    self.install_python_packages(packages=new_deps)

    def no_base_python_found(self, base_pythons: List[str]) -> NoReturn:
        raise NoInterpreter(base_pythons)

    @abstractmethod
    def requires(self) -> List[Requirement]:
        raise NotImplementedError

    @abstractmethod
    def build_requires(self) -> List[Requirement]:
        raise NotImplementedError

    def default_base_python(self, conf: Config, env_name: Optional[str]) -> List[str]:
        return [sys.executable]
