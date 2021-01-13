"""
A tox python environment runner that uses the virtualenv project.
"""
from pathlib import Path
from typing import Dict, Generator, Optional, Set, Tuple

from tox.config.cli.parser import Parsed
from tox.config.main import Config
from tox.config.sets import CoreConfigSet, EnvConfigSet
from tox.journal import EnvJournal
from tox.plugin.impl import impl
from tox.report import HandledError, ToxHandler
from tox.tox_env.package import PackageToxEnv
from tox.tox_env.register import ToxEnvRegister

from ..runner import PythonRun
from .api import VirtualEnv
from .package.api import PackageType


class VirtualEnvRunner(VirtualEnv, PythonRun):
    """local file system python virtual environment via the virtualenv package"""

    def __init__(
        self, conf: EnvConfigSet, core: CoreConfigSet, options: Parsed, journal: EnvJournal, log_handler: ToxHandler
    ) -> None:
        super().__init__(conf, core, options, journal, log_handler)

    @staticmethod
    def id() -> str:
        return "virtualenv"

    def add_package_conf(self) -> bool:
        desc = f"package installation mode - {' | '.join(i.name for i in PackageType)} "
        if not super().add_package_conf():
            self.conf.add_constant(["package"], desc, PackageType.skip)
            return False
        self.conf.add_config(keys="usedevelop", desc="use develop mode", default=False, of_type=bool)
        develop_mode = self.conf["usedevelop"] or getattr(self.options, "develop", False)
        if develop_mode:
            self.conf.add_constant(["package"], desc, PackageType.dev)
        else:
            self.conf.add_config(keys="package", of_type=PackageType, default=PackageType.sdist, desc=desc)
        pkg_type = self.pkg_type

        if pkg_type == PackageType.skip:
            return False

        self.conf.add_constant(
            keys=["package_tox_env_type"],
            desc="tox package type used to package",
            value="virtualenv-pep-517",
        )

        self.conf.add_config(
            keys=["package_env", "isolated_build_env"],
            of_type=str,
            default=".pkg",
            desc="tox environment used to package",
        )

        if pkg_type == PackageType.wheel:

            def default_wheel_tag(conf: "Config", env_name: Optional[str]) -> str:
                # https://www.python.org/dev/peps/pep-0427/#file-name-convention
                # when building wheels we need to ensure that the built package is compatible with the target env
                # compatibility is documented within https://www.python.org/dev/peps/pep-0427/#file-name-convention
                # a wheel tag example: {distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl
                # python only code are often compatible at major level (unless universal wheel in which case both 2/3)
                # c-extension codes are trickier, but as of today both poetry/setuptools uses pypa/wheels logic
                # https://github.com/pypa/wheel/blob/master/src/wheel/bdist_wheel.py#L234-L280
                base: str = self.conf["package_env"]
                run = self.base_python
                if run is not None and self.package_env is not None and isinstance(self.package_env, VirtualEnv):
                    pkg = self.package_env.base_python
                    if pkg.version_no_dot == run.version_no_dot and pkg.impl_lower == run.impl_lower:
                        return base
                if run is None:
                    raise ValueError(f"could not resolve base python for {self.conf.name}")
                return f"{base}-{run.impl_lower}{run.version_no_dot}"

            self.conf.add_config(
                keys=["wheel_build_env"],
                of_type=str,
                default=default_wheel_tag,
                desc="wheel tag to use for building applications",
            )
        self.conf.add_config(
            keys=["extras"],
            of_type=Set[str],
            default=set(),
            desc="extras to install of the target package",
        )
        return True

    def create_package_env(self) -> Generator[Tuple[str, str], PackageToxEnv, None]:
        yield from super().create_package_env()
        if self.package_env is not None:
            pkg_env = self.package_env
            wheel_build_env = self.conf["wheel_build_env"] if self.pkg_type is PackageType.wheel else pkg_env.conf.name
            yield from self.package_env.create_package_env(self.conf.name, (self.pkg_type, wheel_build_env))

    def teardown(self) -> None:
        super().teardown()

    @property
    def pkg_type(self) -> PackageType:
        try:
            pkg_type: PackageType = self.conf["package"]
        except AttributeError as exc:
            values = ", ".join(i.name for i in PackageType)
            error = HandledError(f"invalid package config type {exc.args[0]!r} requested, must be one of {values}")
            raise error from exc
        return pkg_type

    def install_package_args(self) -> Dict[str, bool]:
        return {
            "no_deps": True,  # dependencies are installed separately
            "develop": self.pkg_type is PackageType.dev,  # if package type is develop mode pass option through
            "force_reinstall": True,  # if is already installed reinstall
        }

    def install_requirement_file(self, path: Path) -> None:
        install_command = self.base_install_cmd + ["-r", str(path)]
        result = self.perform_install(install_command, "install_deps")
        result.assert_success()


@impl
def tox_register_tox_env(register: ToxEnvRegister) -> None:
    register.add_run_env(VirtualEnvRunner)
