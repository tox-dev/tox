"""
A tox python environment runner that uses the virtualenv project.
"""
from typing import Optional, Set

from tox.config.main import Config
from tox.plugin.impl import impl
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

    def add_package_conf(self) -> bool:
        if super().add_package_conf() is False:
            return False
        self.conf.add_config(
            keys="package",
            of_type=PackageType,
            default=PackageType.sdist,
            desc=f"package installation mode - {' | '.join(i.name for i in PackageType)} ",
        )
        pkg_type: PackageType = self.conf["package"]
        if pkg_type == PackageType.skip:
            return False
        self.conf.add_constant(
            keys=["package_tox_env_type"],
            desc="tox package type used to package",
            value=virtual_env_package_id(pkg_type),
        )

        def default_package_name(conf: Config, name: Optional[str]) -> str:
            result = ".package"

            # when building wheels we need to ensure that the built package is compatible with the target environment
            # compatibility is documented within https://www.python.org/dev/peps/pep-0427/#file-name-convention
            # a wheel tag looks like: {distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl
            # python only code are often compatible at major level (unless universal wheel in which case both 2 and 3)
            # c-extension codes are trickier, but as of today both poetry/setuptools uses pypa/wheels logic
            # https://github.com/pypa/wheel/blob/master/src/wheel/bdist_wheel.py#L234-L280
            # technically, the build tags can be passed in as CLI args to the build backend, but for now it's easier
            # to just create a new build env for every target env
            if pkg_type is PackageType.wheel:
                result = f"{result}-{self.conf['env_name']}"
            return result

        self.conf.add_config(
            keys=["package_env", "isolated_build_env"],
            of_type=str,
            default=default_package_name,
            desc="tox environment used to package",
        )
        self.conf.add_config(
            keys=["extras"],
            of_type=Set[str],
            default=set(),
            desc="extras to install of the target package",
        )
        return True

    def install_package(self) -> None:
        if self.package_env is not None:
            package = self.package_env.perform_packaging()
            if package:
                develop = self.conf["package"] is PackageType.dev
                self.install_python_packages(package, no_deps=True, develop=develop, force_reinstall=True)


@impl
def tox_register_tox_env(register: ToxEnvRegister) -> None:
    register.add_run_env(VirtualEnvRunner)
