import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Generator, List, Optional, Tuple, cast

from tox.config.sets import CoreConfigSet, EnvConfigSet
from tox.config.types import Command, EnvList
from tox.journal import EnvJournal
from tox.report import ToxHandler

from .api import ToxEnv
from .package import PackageToxEnv

if TYPE_CHECKING:
    from tox.config.cli.parser import Parsed


class RunToxEnv(ToxEnv, ABC):
    def __init__(
        self, conf: EnvConfigSet, core: CoreConfigSet, options: "Parsed", journal: EnvJournal, log_handler: ToxHandler
    ) -> None:
        self.has_package = False
        self.package_env: Optional[PackageToxEnv] = None
        super().__init__(conf, core, options, journal, log_handler)

    def register_config(self) -> None:
        super().register_config()
        self.conf.add_config(
            keys=["description"],
            of_type=str,
            default="",
            desc="description attached to the tox environment",
        )
        self.conf.add_config(
            keys=["commands"],
            of_type=List[Command],
            default=[],
            desc="the commands to be called for testing",
        )
        self.conf.add_config(
            keys=["commands_pre"],
            of_type=List[Command],
            default=[],
            desc="the commands to be called before testing",
        )
        self.conf.add_config(
            keys=["commands_post"],
            of_type=List[Command],
            default=[],
            desc="the commands to be called after testing",
        )
        self.conf.add_config(
            keys=["change_dir", "changedir"],
            of_type=Path,
            default=lambda conf, name: cast(Path, conf.core["tox_root"]),
            desc="Change to this working directory when executing the test command.",
        )
        self.conf.add_config(
            "depends",
            of_type=EnvList,
            desc="tox environments that this environment depends on (must be run after those)",
            default=EnvList([]),
        )
        self.has_package = self.add_package_conf()

    def add_package_conf(self) -> bool:
        """If this returns True package_env and package_tox_env_type configurations must be defined"""
        self.core.add_config(
            keys=["no_package", "skipsdist"],
            of_type=bool,
            default=False,
            desc="Is there any packaging involved in this project.",
        )
        core_no_package: bool = self.core["no_package"]
        if core_no_package is True:
            return False
        self.conf.add_config(
            keys="skip_install",
            of_type=bool,
            default=False,
            desc="skip installation",
        )
        skip_install: bool = self.conf["skip_install"]
        return not skip_install

    def create_package_env(self) -> Generator[Tuple[str, str], PackageToxEnv, None]:
        if not self.has_package:
            return
        core_type = self.conf["package_tox_env_type"]
        name = self.conf["package_env"]
        package_tox_env = yield name, core_type
        self.package_env = package_tox_env
        self.package_env.ref_count.increment()

    def clean(self, force: bool = False) -> None:
        super().clean(force)
        if self.package_env is not None:  # pragma: no cover branch
            with self.package_env.display_context(suspend=self.has_display_suspended):
                self.package_env.clean()  # do not pass force along, allow package env to ignore if requested

    @property
    def environment_variables(self) -> Dict[str, str]:
        environment_variables = super().environment_variables
        if self.has_package:  # if package(s) have been built insert them as environment variable
            if self.packages:
                environment_variables["TOX_PACKAGE"] = os.pathsep.join(self.packages)
        return environment_variables

    @property
    @abstractmethod
    def packages(self) -> List[str]:
        """:returns: a list of packages installed in the environment"""
        raise NotImplementedError

    def teardown(self) -> None:
        super().teardown()
        if self.package_env is not None:
            with self.package_env.display_context(suspend=self.has_display_suspended):
                self.package_env.teardown()

    def interrupt(self) -> None:
        super().interrupt()
        if self.package_env is not None:  # pragma: no branch
            self.package_env.interrupt()

    def package_envs(self) -> Generator[PackageToxEnv, None, None]:
        if self.package_env is not None and self.conf.name is not None:
            yield from self.package_env.package_envs(self.conf.name)
