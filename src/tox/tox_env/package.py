"""
A tox environment that can build packages.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Any, Generator, List, Set, Tuple, cast

from tox.config.sets import CoreConfigSet, EnvConfigSet
from tox.journal import EnvJournal
from tox.report import ToxHandler

from .api import ToxEnv

if TYPE_CHECKING:
    from tox.config.cli.parser import Parsed


class Package:
    """package"""


class PathPackage(Package):
    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path

    def __str__(self) -> str:
        return str(self.path)


class PackageToxEnv(ToxEnv, ABC):
    def __init__(
        self, conf: EnvConfigSet, core: CoreConfigSet, options: "Parsed", journal: EnvJournal, log_handler: ToxHandler
    ) -> None:
        super().__init__(conf, core, options, journal, log_handler)
        self.recreate_package = options.recreate and not options.no_recreate_pkg
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

    def create_package_env(
        self, name: str, info: Tuple[Any, ...]  # noqa: U100
    ) -> Generator[Tuple[str, str], "PackageToxEnv", None]:
        """allow creating sub-package envs"""

    @abstractmethod
    def perform_packaging(self, for_env: EnvConfigSet) -> List[Package]:  # noqa: U100
        raise NotImplementedError

    def _clean(self, force: bool = False) -> None:
        if force or self.recreate_package:  # only recreate if user did not opt out
            super()._clean(force)

    def notify_of_run_env(self, conf: EnvConfigSet) -> None:
        with self._lock:
            self._envs.add(conf.name)

    def teardown_env(self, conf: EnvConfigSet) -> None:
        with self._lock:
            self._envs.remove(conf.name)
            has_envs = bool(self._envs)
        if not has_envs:
            self._teardown()
