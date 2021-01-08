"""
A tox environment that can build packages.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, List, Set

from packaging.requirements import Requirement

from tox.config.sets import ConfigSet
from tox.journal import EnvJournal
from tox.report import ToxHandler
from tox.util.threading import AtomicCounter

from .api import ToxEnv

if TYPE_CHECKING:
    from tox.config.cli.parser import Parsed


class PackageToxEnv(ToxEnv, ABC):
    def __init__(
        self, conf: ConfigSet, core: ConfigSet, options: "Parsed", journal: EnvJournal, log_handler: ToxHandler
    ) -> None:
        super().__init__(conf, core, options, journal, log_handler)
        self.recreate_package = options.no_recreate_pkg is False if options.recreate else False
        self.ref_count = AtomicCounter()

    @abstractmethod
    def get_package_dependencies(self, extras: Set[str]) -> List[Requirement]:
        raise NotImplementedError

    @abstractmethod
    def perform_packaging(self) -> List[Path]:
        raise NotImplementedError

    def clean(self, force: bool = False) -> None:
        if force or self.recreate_package:  # only recreate if user did not opt out
            super().clean(force)
