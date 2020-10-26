from abc import ABC
from pathlib import Path
from typing import TYPE_CHECKING, Generator, List, Optional, Tuple, cast

from tox.config.sets import ConfigSet
from tox.config.source.api import Command, EnvList

from .api import ToxEnv
from .package import PackageToxEnv

if TYPE_CHECKING:
    from tox.config.cli.parser import Parsed


class RunToxEnv(ToxEnv, ABC):
    def __init__(self, conf: ConfigSet, core: ConfigSet, options: "Parsed") -> None:
        self.has_package = False
        self.package_env: Optional[PackageToxEnv] = None
        super().__init__(conf, core, options)

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
        self.conf.add_config(
            "parallel_show_output",
            of_type=bool,
            default=False,
            desc="if set to True the content of the output will always be shown  when running in parallel mode",
        )
        self.has_package = self.add_package_conf()

    def add_package_conf(self) -> bool:
        """If this returns True package_env and package_tox_env_type configurations must be defined"""
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
        if skip_install:
            return False
        return True

    def set_package_env(self) -> Generator[Tuple[str, str], PackageToxEnv, None]:
        if not self.has_package:
            return
        of_type = self.conf["package_tox_env_type"]
        name = self.conf["package_env"]
        package_tox_env = yield name, of_type
        self.package_env = package_tox_env

    def clean(self, package_env: bool = True) -> None:
        super().clean()
        if self.package_env:
            self.package_env.clean()
