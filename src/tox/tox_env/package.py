from abc import ABC, abstractmethod
from typing import Any, List

from .api import ToxEnv


class PackageToxEnv(ToxEnv, ABC):
    def register_config(self):
        super().register_config()

    @abstractmethod
    def get_package_dependencies(self, extras=None) -> List[Any]:
        raise NotImplementedError

    @abstractmethod
    def perform_packaging(self) -> List[Any]:
        raise NotImplementedError
