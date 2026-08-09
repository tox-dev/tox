"""Pin the inference behavior of the typed config and installer APIs (checked statically, never imported)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from typing_extensions import assert_type

from tox.config.of_type import ConfigDynamicDefinition
from tox.config.sets import ConfigSet
from tox.tox_env.api import ToxEnv
from tox.tox_env.installer import Installer

if TYPE_CHECKING:
    from tox.config.main import Config
    from tox.tox_env.installer import InstallArguments


class CheckConfigSet(ConfigSet):
    def register_config(self) -> None:
        with_callable_default = self.add_config(
            keys="a", of_type=Path, default=self._default_path, desc="d", post_process=self._keep
        )
        assert_type(with_callable_default, ConfigDynamicDefinition[Path])
        with_none_default = self.add_config(keys="b", of_type=str, default=None, desc="d")
        assert_type(with_none_default, ConfigDynamicDefinition[str | None])
        with_container = self.add_config(keys="c", of_type=list[str], default=["x"], desc="d")
        assert_type(with_container, ConfigDynamicDefinition[list[str]])
        assert_type(self.get("a", Path), Path)
        assert_type(self.get("c", list[str]), list[str])

    def _default_path(self, conf: Config, env_name: str | None) -> Path:
        raise NotImplementedError

    @staticmethod
    def _keep(value: Path) -> Path:
        raise NotImplementedError


class CheckInstallerDefaultArgs(Installer[ToxEnv]):
    """A single type parameter must keep working, defaulting the arguments to ``InstallArguments``."""

    def _register_config(self) -> None:
        raise NotImplementedError

    def installed(self) -> list[str]:
        raise NotImplementedError

    def install(self, arguments: InstallArguments, section: str, of_type: str) -> None:
        raise NotImplementedError
