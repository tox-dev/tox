"""
A tox python environment runner that uses the virtualenv project.
"""
from typing import Optional, Tuple

from tox.plugin.impl import impl
from tox.tox_env.python.virtual_env.package.artifact.wheel import (
    Pep517VirtualEnvPackageWheel,
)
from tox.tox_env.register import ToxEnvRegister

from ..runner import PythonRun
from .api import VirtualEnv
from .package.api import PackageType
from .package.util import virtual_env_package_id


class VirtualEnvRunner(VirtualEnv, PythonRun):
    """local file system python virtual environment via the virtualenv package"""

    @staticmethod
    def id() -> str:
        return "virtualenv"

    def add_package_conf(self) -> None:
        if self.core["no_package"] is True:
            return
        self.conf.add_config(
            keys="package",
            of_type=PackageType,
            default=PackageType.sdist,
            desc=f"package installation mode - {' | '.join(i.name for i in PackageType)} ",
        )
        if self.conf["package"] == PackageType.skip:
            return
        super().add_package_conf()
        self.core.add_config(
            keys=["package_env", "isolated_build_env"],
            of_type=str,
            default=".package",
            desc="tox environment used to package",
        )
        package = self.conf["package"]
        self.conf.add_config(
            keys="package_tox_env_type",
            of_type=str,
            default=virtual_env_package_id(package),
            desc="tox package type used to package",
        )
        if self.conf["package"] is PackageType.wheel:
            self.conf.add_config(
                keys="universal_wheel",
                of_type=bool,
                default=Pep517VirtualEnvPackageWheel.default_universal_wheel(self.core),
                desc="tox package type used to package",
            )

    def has_package(self) -> bool:
        return self.core["no_package"] or self.conf["package"] is not PackageType.skip

    def package_env_name_type(self) -> Optional[Tuple[str, str]]:
        if not self.has_package():
            return None
        package = self.conf["package"]
        package_env_type = self.conf["package_tox_env_type"]
        name = self.core["package_env"]
        # we can get away with a single common package if: sdist, dev, universal wheel
        if package is PackageType.wheel and self.conf["universal_wheel"] is False:
            # if version specific wheel one per env
            name = "{}-{}".format(name, self.conf["env_name"])
        return name, package_env_type

    def install_package(self) -> None:
        if self.package_env is not None:
            package = self.package_env.perform_packaging()
            if package:
                develop = self.conf["package"] is PackageType.dev
                self.install_python_packages(package, no_deps=True, develop=develop, force_reinstall=True)


@impl
def tox_register_tox_env(register: ToxEnvRegister) -> None:
    register.add_run_env(VirtualEnvRunner)
