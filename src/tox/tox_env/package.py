"""
A tox environment that can build packages.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from threading import Lock
from typing import Any, Generator, List, Optional, Set, Tuple, cast

from tox.config.main import Config
from tox.config.sets import EnvConfigSet

from .api import ToxEnv, ToxEnvCreateArgs


class Package:
    """package"""


class PathPackage(Package):
    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path

    def __str__(self) -> str:
        return str(self.path)


class PackageToxEnv(ToxEnv, ABC):
    def __init__(self, create_args: ToxEnvCreateArgs) -> None:
        super().__init__(create_args)
        self._envs: Set[str] = set()
        self._lock = Lock()

    def register_config(self) -> None:
        super().register_config()
        self.core.add_config(
            keys=["package_root", "setupdir"],
            of_type=Path,
            default=cast(Path, self.core["tox_root"]),
            desc="indicates where the packaging root file exists (historically setup.py file or pyproject.toml now)",
        )
        self.conf.add_config(
            keys=["package_root", "setupdir"],
            of_type=Path,
            default=cast(Path, self.core["package_root"]),
            desc="indicates where the packaging root file exists (historically setup.py file or pyproject.toml now)",
        )

    def _recreate_default(self, conf: "Config", value: Optional[str]) -> bool:
        return self.options.no_recreate_pkg is False and super()._recreate_default(conf, value)

    def create_package_env(
        self, name: str, info: Tuple[Any, ...]  # noqa: U100
    ) -> Generator[Tuple[str, str], "PackageToxEnv", None]:
        """allow creating sub-package envs"""

    @abstractmethod
    def perform_packaging(self, for_env: EnvConfigSet) -> List[Package]:  # noqa: U100
        raise NotImplementedError

    def notify_of_run_env(self, conf: EnvConfigSet) -> None:
        with self._lock:
            self._envs.add(conf.name)

    def teardown_env(self, conf: EnvConfigSet) -> None:
        with self._lock:
            self._envs.remove(conf.name)
            has_envs = bool(self._envs)
        if not has_envs:
            self._teardown()
