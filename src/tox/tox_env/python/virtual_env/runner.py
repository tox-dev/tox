"""
A tox python environment runner that uses the virtualenv project.
"""
from typing import Dict, Optional, Set

from tox.config.main import Config
from tox.plugin.impl import impl
from tox.report import HandledError
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
        if not super().add_package_conf():
            return False
        self.conf.add_config(keys="usedevelop", desc="use develop mode", default=False, of_type=bool)
        develop_mode = self.conf["usedevelop"]
        desc = f"package installation mode - {' | '.join(i.name for i in PackageType)} "
        if develop_mode:
            self.conf.add_constant(["package"], desc, PackageType.dev)
        else:
            self.conf.add_config(keys="package", of_type=PackageType, default=PackageType.sdist, desc=desc)
        try:
            pkg_type: PackageType = self.conf["package"]
        except AttributeError as exc:
            values = ", ".join(i.name for i in PackageType)
            raise HandledError(f"invalid package config type {exc.args[0]!r} requested, must be one of {values}")

        if pkg_type == PackageType.skip:
            return False

        self.conf.add_constant(
            keys=["package_tox_env_type"],
            desc="tox package type used to package",
            value=virtual_env_package_id(pkg_type),
        )

        def default_package_name(conf: Config, name: Optional[str]) -> str:
            result = ".package"

            # when building wheels we need to ensure that the built package is compatible with the target env
            # compatibility is documented within https://www.python.org/dev/peps/pep-0427/#file-name-convention
            # a wheel tag example: {distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl
            # python only code are often compatible at major level (unless universal wheel in which case both 2/3)
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

    def install_package_args(self) -> Dict[str, bool]:
        return {
            "no_deps": True,  # dependencies are installed separately
            "develop": self.conf["package"] is PackageType.dev,  # if package type is develop mode pass option through
            "force_reinstall": True,  # if is already installed reinstall
        }

    def install_deps(self) -> None:
        super().install_deps()
        if self.package_env is not None:
            package_deps = self.package_env.package_deps()
            if package_deps:
                self.cached_install(package_deps, PythonRun.__name__, "build-deps")


@impl
def tox_register_tox_env(register: ToxEnvRegister) -> None:
    register.add_run_env(VirtualEnvRunner)
