from typing import TYPE_CHECKING, Dict, Iterable, Type

from .package import PackageToxEnv
from .runner import RunToxEnv

if TYPE_CHECKING:
    from tox.plugin.manager import Plugin


class ToxEnvRegister:
    def __init__(self) -> None:
        self._run_envs: Dict[str, Type[RunToxEnv]] = {}
        self._package_envs: Dict[str, Type[PackageToxEnv]] = {}
        self._default_run_env: str = ""

    def populate(self, manager: "Plugin") -> None:
        manager.tox_register_tox_env(register=self)
        self._default_run_env = next(iter(self._run_envs.keys()))

    def add_run_env(self, of_type: Type[RunToxEnv]) -> None:
        self._run_envs[of_type.id()] = of_type

    def add_package_env(self, of_type: Type[PackageToxEnv]) -> None:
        self._package_envs[of_type.id()] = of_type

    @property
    def run_envs(self) -> Iterable[str]:
        return self._run_envs.keys()

    @property
    def default_run_env(self) -> str:
        return self._default_run_env

    @default_run_env.setter
    def default_run_env(self, value: str) -> None:
        if value not in self._run_envs:
            raise ValueError("run env must be registered before setting it as default")
        self._default_run_env = value

    def runner(self, name: str) -> Type[RunToxEnv]:
        return self._run_envs[name]

    def package(self, name: str) -> Type[PackageToxEnv]:
        return self._package_envs[name]


REGISTER = ToxEnvRegister()
