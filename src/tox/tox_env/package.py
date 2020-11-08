"""
A tox environment that can build packages.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Set

from packaging.requirements import Requirement

from tox.config.sets import ConfigSet
from tox.journal import EnvJournal
from tox.tox_env.errors import Recreate

from .api import ToxEnv

if TYPE_CHECKING:
    from tox.config.cli.parser import Parsed
    from tox.tox_env.python.api import Deps


class PackageToxEnv(ToxEnv, ABC):
    def __init__(self, conf: ConfigSet, core: ConfigSet, options: "Parsed", journal: EnvJournal) -> None:
        super().__init__(conf, core, options, journal)
        self._cleaned = False
        self._setup_done = False

    def register_config(self) -> None:
        super().register_config()

    @abstractmethod
    def get_package_dependencies(self, extras: Optional[Set[str]] = None) -> List[Requirement]:
        raise NotImplementedError

    @abstractmethod
    def perform_packaging(self) -> List[Path]:
        raise NotImplementedError

    def clean(self) -> None:
        # package environments may be shared clean only once
        if self._cleaned is False:
            self._cleaned = True
            super().clean()

    def ensure_setup(self) -> None:
        if self._setup_done is False:
            try:
                self.setup()
            except Recreate:
                self.clean()
                self.setup()
            self.setup_done()
        self._setup_done = True

    def package_deps(self) -> "Deps":
        return []
