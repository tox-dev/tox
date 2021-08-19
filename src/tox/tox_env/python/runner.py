"""
A tox run environment that handles the Python language.
"""
from abc import ABC
from pathlib import Path
from typing import Iterator, List, Optional, Set, Tuple

from tox.config.main import Config
from tox.report import HandledError
from tox.tox_env.errors import Skip
from tox.tox_env.package import Package, PathPackage
from tox.tox_env.python.package import PythonPackageToxEnv
from tox.tox_env.python.pip.req_file import PythonDeps

from ..api import ToxEnvCreateArgs
from ..runner import RunToxEnv
from .api import Python


class PythonRun(Python, RunToxEnv, ABC):
    def __init__(self, create_args: ToxEnvCreateArgs) -> None:
        super().__init__(create_args)

    def register_config(self) -> None:
        super().register_config()
        deps_kwargs = {"root": self.core["toxinidir"]}
        self.conf.add_config(
            keys="deps",
            of_type=PythonDeps,
            kwargs=deps_kwargs,
            default=PythonDeps("", **deps_kwargs),
            desc="Name of the python dependencies as specified by PEP-440",
        )
        self.core.add_config(
            keys=["skip_missing_interpreters"],
            default=True,
            of_type=bool,
            desc="skip running missing interpreters",
        )

    def iter_package_env_types(self) -> Iterator[Tuple[str, str, str]]:
        yield from super().iter_package_env_types()
        if self.pkg_type == "wheel":
            wheel_build_env: str = self.conf["wheel_build_env"]
            if wheel_build_env not in self._package_envs:  # pragma: no branch
                package_tox_env_type = self.conf["package_tox_env_type"]
                yield "wheel", wheel_build_env, package_tox_env_type

    @property
    def _package_types(self) -> Tuple[str, ...]:
        return "wheel", "sdist", "dev-legacy", "skip"

    def _register_package_conf(self) -> bool:
        desc = f"package installation mode - {' | '.join(i for i in self._package_types)} "
        if not super()._register_package_conf():
            self.conf.add_constant(["package"], desc, "skip")
            return False
        self.conf.add_config(keys=["use_develop", "usedevelop"], desc="use develop mode", default=False, of_type=bool)
        develop_mode = self.conf["use_develop"] or getattr(self.options, "develop", False)
        if develop_mode:
            self.conf.add_constant(["package"], desc, "dev-legacy")
        else:
            self.conf.add_config(keys="package", of_type=str, default="sdist", desc=desc)
        pkg_type = self.pkg_type

        if pkg_type == "skip":
            return False

        if pkg_type == "wheel":

            def default_wheel_tag(conf: "Config", env_name: Optional[str]) -> str:
                # https://www.python.org/dev/peps/pep-0427/#file-name-convention
                # when building wheels we need to ensure that the built package is compatible with the target env
                # compatibility is documented within https://www.python.org/dev/peps/pep-0427/#file-name-convention
                # a wheel tag example: {distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl
                # python only code are often compatible at major level (unless universal wheel in which case both 2/3)
                # c-extension codes are trickier, but as of today both poetry/setuptools uses pypa/wheels logic
                # https://github.com/pypa/wheel/blob/master/src/wheel/bdist_wheel.py#L234-L280
                default_package_env = self._package_envs["default"]
                self_py = self.base_python
                if self_py is not None and isinstance(default_package_env, PythonPackageToxEnv):
                    default_pkg_py = default_package_env.base_python
                    if (
                        default_pkg_py.version_no_dot == self_py.version_no_dot
                        and default_pkg_py.impl_lower == self_py.impl_lower
                    ):
                        return default_package_env.conf.name
                if self_py is None:
                    raise ValueError(f"could not resolve base python for {self.conf.name}")
                return f"{default_package_env.conf.name}-{self_py.impl_lower}{self_py.version_no_dot}"

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

    @property
    def pkg_type(self) -> str:
        pkg_type: str = self.conf["package"]
        if pkg_type not in self._package_types:
            values = ", ".join(self._package_types)
            raise HandledError(f"invalid package config type {pkg_type} requested, must be one of {values}")
        return pkg_type

    def _setup_env(self) -> None:
        super()._setup_env()
        self._install_deps()

    def _install_deps(self) -> None:
        requirements_file: PythonDeps = self.conf["deps"]
        self.installer.install(requirements_file, PythonRun.__name__, "deps")

    def _build_packages(self) -> List[Package]:
        explicit_install_package: Optional[Path] = getattr(self.options, "install_pkg", None)
        if explicit_install_package is not None:
            return [PathPackage(explicit_install_package)]

        package_env = self._package_envs[self._get_package_env()]
        with package_env.display_context(self._has_display_suspended):
            try:
                packages = package_env.perform_packaging(self.conf)
            except Skip as exception:
                raise Skip(f"{exception.args[0]} for package environment {package_env.conf['env_name']}")
        return packages

    def _get_package_env(self) -> str:
        return "wheel" if self.pkg_type == "wheel" else "default"
