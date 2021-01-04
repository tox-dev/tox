"""
A tox environment that can build packages.
"""
from abc import ABC, abstractmethod
from argparse import ArgumentParser
from pathlib import Path
from typing import TYPE_CHECKING, List, Set

from packaging.requirements import Requirement

from tox.config.sets import ConfigSet
from tox.journal import EnvJournal
from tox.plugin.impl import impl
from tox.report import ToxHandler
from tox.util.threading import AtomicCounter

from .api import ToxEnv

if TYPE_CHECKING:
    from tox.config.cli.parser import Parsed
    from tox.tox_env.python.api import PythonDeps


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

    def package_deps(self) -> "PythonDeps":
        return []

    def clean(self) -> None:
        if self.recreate_package:  # only recreate if user did not opt out
            super().clean()


@impl
def tox_add_option(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--no-recreate-pkg",
        dest="no_recreate_pkg",
        help="if recreate is set do not recreate packaging tox environment(s)",
        action="store_true",
    )
