"""
Manages the tox environment registry.
"""
from typing import TYPE_CHECKING, Dict, Iterable, Type

from .package import PackageToxEnv
from .runner import RunToxEnv

if TYPE_CHECKING:
    from tox.plugin.manager import Plugin


class ToxEnvRegister:
    """tox environment registry"""

    def __init__(self) -> None:
        self._run_envs: Dict[str, Type[RunToxEnv]] = {}
        self._package_envs: Dict[str, Type[PackageToxEnv]] = {}
        self._default_run_env: str = ""

    def _register_tox_env_types(self, manager: "Plugin") -> None:
        manager.tox_register_tox_env(register=self)
        if not self._default_run_env:
            self._default_run_env = next(iter(self._run_envs.keys()))

    def add_run_env(self, of_type: Type[RunToxEnv]) -> None:
        """
        Define a new run tox environment type.

        :param of_type: the new run environment type
        """
        self._run_envs[of_type.id()] = of_type

    def add_package_env(self, of_type: Type[PackageToxEnv]) -> None:
        """
        Define a new packaging tox environment type.

        :param of_type: the new packaging environment type
        """
        self._package_envs[of_type.id()] = of_type

    @property
    def run_envs(self) -> Iterable[str]:
        """:returns: run environment types currently defined"""
        return self._run_envs.keys()

    @property
    def default_run_env(self) -> str:
        """:returns: the default run environment type"""
        return self._default_run_env

    @default_run_env.setter
    def default_run_env(self, value: str) -> None:
        """
        Change the default run environment type.

        :param value: the new run environment type by name
        """
        if value not in self._run_envs:
            raise ValueError("run env must be registered before setting it as default")
        self._default_run_env = value

    def runner(self, name: str) -> Type[RunToxEnv]:
        """
        Lookup a run tox environment type by name.

        :param name: the name of the runner type
        :return: the type of the runner type
        """
        return self._run_envs[name]

    def package(self, name: str) -> Type[PackageToxEnv]:
        """
        Lookup a packaging tox environment type by name.

        :param name: the name of the packaging type
        :return: the type of the packaging type
        """
        return self._package_envs[name]


REGISTER = ToxEnvRegister()  #: the tox register

__all__ = (
    "REGISTER",
    "ToxEnvRegister",
)
