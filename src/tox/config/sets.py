from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar, cast, get_origin, overload

from tox.util.typing_compat import override

from .of_type import ConfigConstantDefinition, ConfigDefinition, ConfigDynamicDefinition, ConfigLoadArgs
from .set_env import SetEnv, SetEnvRaw, SetEnvReference, SetEnvValue
from .types import EnvList

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterator, Mapping, Sequence
    from types import UnionType
    from typing import Final

    from .loader.api import Loader
    from .loader.convert import Factory
    from .loader.section import Section
    from .main import Config

V = TypeVar("V")  # simplint: ignore[SMP101, SMP404]  # exported, renaming breaks importers


class ConfigSet(ABC):
    """A set of configuration that belong together (such as a tox environment settings, core tox settings).

    :param conf: the global tox configuration
    :param section: the section that holds the raw values of this set
    :param env_name: the tox environment name, or ``None`` for the core set

    """

    def __init__(self, conf: Config, section: Section, env_name: str | None) -> None:
        self._section = section
        self._env_name = env_name
        self._conf = conf
        self.loaders: list[Loader[Any]] = []  #: active configuration loaders, can alter to change configuration values
        self._defined: dict[str, ConfigDefinition[Any]] = {}
        self._keys: dict[str, None] = {}
        self._alias: dict[str, str] = {}
        self._final = False
        self.register_config()

    @abstractmethod
    def register_config(self) -> None:
        """Register the configuration keys this set provides."""
        raise NotImplementedError

    def __getitem__(self, item: str) -> Any:
        """Get the config value for a given key (will materialize in case of dynamic config).

        :param item: the config key

        :returns: the configuration value

        """
        return self.load(item)

    def load(self, item: str, chain: list[str] | None = None) -> Any:
        """Get the config value for a given key (will materialize in case of dynamic config).

        :param item: the config key
        :param chain: a chain of configuration keys already loaded for this load operation (used to detect circles)

        :returns: the configuration value

        """
        return self._defined[item].__call__(  # ruff:ignore[unnecessary-dunder-call]  # explicit dunder call
            self._conf, self.loaders, ConfigLoadArgs(chain, self.name, self.env_name)
        )

    @property
    def name(self) -> str:
        """The name of the section this set reads its configuration from."""
        return self._section.name

    @property
    def env_name(self) -> str | None:
        """The name of the environment this set belongs to, ``None`` for the core configuration."""
        return self._env_name

    @override
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(loaders={self.loaders!r})"

    def __iter__(self) -> Iterator[str]:
        """:returns: iterate through the defined config keys (primary keys used)"""
        return iter(self._keys.keys())

    def __contains__(self, item: str) -> bool:
        """Check if a configuration key is within the config set.

        :param item: the configuration value

        :returns: a boolean indicating the truthiness of the statement

        """
        return item in self._alias

    def get_configs(self) -> Generator[ConfigDefinition[Any], None, None]:
        """Iterate over the config definitions, one per config.

        :yields: the definition of each config, keyed by its first key

        """
        for key, definition in self._defined.items():
            if key == next(iter(definition.keys)):
                yield definition

    def mark_finalized(self) -> None:
        """Mark the set as final, after which no further configuration can be added."""
        self._final = True

    @overload
    def add_config(
        self,
        keys: str | Sequence[str],
        of_type: type[V],
        default: Callable[[Config, str | None], V],
        desc: str,
        post_process: Callable[[V], V] | None = None,
        factory: Factory[Any] | None = None,
    ) -> ConfigDynamicDefinition[V]: ...

    @overload
    def add_config(
        self,
        keys: str | Sequence[str],
        of_type: type[V],
        default: None,
        desc: str,
        post_process: Callable[[V | None], V | None] | None = None,
        factory: Factory[Any] | None = None,
    ) -> ConfigDynamicDefinition[V | None]: ...

    @overload
    def add_config(
        self,
        keys: str | Sequence[str],
        of_type: type[V],
        default: V,
        desc: str,
        post_process: Callable[[V], V] | None = None,
        factory: Factory[Any] | None = None,
    ) -> ConfigDynamicDefinition[V]: ...

    @overload
    def add_config(
        self,
        keys: str | Sequence[str],
        of_type: UnionType,
        default: Callable[[Config, str | None], V],
        desc: str,
        post_process: Callable[[V], V] | None = None,
        factory: Factory[Any] | None = None,
    ) -> ConfigDynamicDefinition[V]: ...

    @overload
    def add_config(
        self,
        keys: str | Sequence[str],
        of_type: UnionType,
        default: Callable[[Config, str | None], V | None] | V | None,
        desc: str,
        post_process: Callable[[V | None], V | None] | None = None,
        factory: Factory[Any] | None = None,
    ) -> ConfigDynamicDefinition[V | None]: ...

    @overload
    def add_config(
        self,
        keys: str | Sequence[str],
        of_type: UnionType,
        default: Callable[[Config, str | None], V] | V,
        desc: str,
        post_process: Callable[[V], V] | None = None,
        factory: Factory[Any] | None = None,
    ) -> ConfigDynamicDefinition[V]: ...

    def add_config(  # ruff:ignore[too-many-arguments]  # public signature
        self,
        keys: str | Sequence[str],
        of_type: type[V] | UnionType,
        default: Callable[[Config, str | None], V] | V | None,
        desc: str,
        post_process: Callable[[V], V] | None = None,
        factory: Factory[Any] | None = None,
    ) -> ConfigDynamicDefinition[V]:
        """Add configuration value.

        :param keys: the keys under what to register the config (first is primary key)
        :param of_type: the type of the config value
        :param default: the default value of the config value
        :param desc: a help message describing the configuration
        :param post_process: a callback to post-process the configuration value after it has been loaded
        :param factory: factory method used to build contained objects (if ``of_type`` is a container type it should
            perform the contained item creation, otherwise creates objects that match the type)

        :returns: the new dynamic config definition

        :raises RuntimeError: when the set has been marked final

        """
        if self._final:
            msg = "config set has been marked final and cannot be extended"
            raise RuntimeError(msg)
        keys_ = self._make_keys(keys)
        result = self._add_conf(keys_, ConfigDynamicDefinition(keys_, desc, of_type, default, post_process, factory))
        return cast("ConfigDynamicDefinition[V]", result)

    @staticmethod
    def _make_keys(keys: str | Sequence[str]) -> Sequence[str]:
        return (keys,) if isinstance(keys, str) else keys

    def _add_conf(self, keys: Sequence[str], definition: ConfigDefinition[V]) -> ConfigDefinition[V]:
        key = keys[0]
        if key in self._defined:
            self._on_duplicate_conf(key, definition)

        self._keys[key] = None
        for item in keys:
            self._alias[item] = key
        for key in keys:
            self._defined[key] = definition
        return definition

    def _on_duplicate_conf(self, key: str, definition: ConfigDefinition[V]) -> None:
        msg = f"duplicate configuration definition for {self.name}:\nhas: {self._defined[key]}\nnew: {definition}"
        raise ValueError(msg)

    def add_constant(self, keys: str | Sequence[str], desc: str, value: V) -> ConfigConstantDefinition[V]:
        """Add a constant value.

        :param keys: the keys under what to register the config (first is primary key)
        :param desc: a help message describing the configuration
        :param value: the config value to use

        :returns: the new constant config value

        :raises RuntimeError: when the set has been marked final

        """
        if self._final:
            msg = "config set has been marked final and cannot be extended"
            raise RuntimeError(msg)
        keys_ = self._make_keys(keys)
        return cast(
            "ConfigConstantDefinition[V]",
            self._add_conf(keys_, ConfigConstantDefinition(keys_, desc, value)),
        )

    def is_constant(self, item: str) -> bool:
        """Check whether a configuration key is a constant.

        :param item: the configuration key

        :returns: whether the key holds a constant value

        """
        return isinstance(self._defined[item], ConfigConstantDefinition)

    def get(self, item: str, of_type: type[V]) -> V:
        """Get the config value for a given key, verified to be of the declared type.

        Unlike :meth:`load` and ``[]`` — which return ``Any`` — the value is checked against ``of_type`` at runtime
        (container types by their unsubscripted origin, so ``list[str]`` checks ``list``) and returned as that type.

        .. versionadded:: 4.59

        :param item: the config key
        :param of_type: the type the config value was registered with

        :returns: the configuration value

        :raises TypeError: when the value is not of the requested type

        """
        value = self.load(item)
        if isinstance(value, get_origin(of_type) or of_type):
            return cast("V", value)
        msg = f"{item} is {type(value).__name__}, expected {of_type!r}"
        raise TypeError(msg)

    def get_optional(self, item: str, of_type: type[V]) -> V | None:
        """Get the config value for a key that may be unset, verified to be of the declared type or ``None``.

        Use this over :meth:`get` for keys registered with a ``None`` default, such as ``min_version``.

        .. versionadded:: 4.62

        :param item: the config key
        :param of_type: the type the config value was registered with

        :returns: the configuration value, or ``None`` when unset

        :raises TypeError: when the value is neither of the requested type nor ``None``

        """
        value = self.load(item)
        if value is None or isinstance(value, get_origin(of_type) or of_type):
            return cast("V | None", value)
        msg = f"{item} is {type(value).__name__}, expected {of_type!r} or None"
        raise TypeError(msg)

    def unused(self) -> list[str]:
        """:returns: Return a list of keys present in the config source but not used"""
        found: set[str] = set()
        # keys within loaders (only if the loader is not a parent too)
        parents = {id(i.parent) for i in self.loaders if i.parent is not None}
        for loader in self.loaders:
            if id(loader) not in parents:
                found.update(loader.found_keys())
        found -= self._defined.keys()
        return sorted(found)

    def primary_key(self, key: str) -> str:
        """Get the primary key for a config key.

        :param key: the config key

        :returns: the key that's considered the primary for the input key

        """
        return self._alias[key]


class CoreConfigSet(ConfigSet):
    """Configuration set for the core tox config.

    :param conf: the global tox configuration
    :param section: the core section of the configuration
    :param root: the directory of the project root
    :param src_path: the path to the configuration file

    """

    def __init__(self, conf: Config, section: Section, root: Path, src_path: Path) -> None:
        self._root = root
        self._src_path = src_path
        super().__init__(conf, section=section, env_name=None)
        desc = "define environments to automatically run"
        self.add_config(keys=["env_list", "envlist"], of_type=EnvList, default=EnvList([]), desc=desc)

    @override
    def register_config(self) -> None:
        self.add_constant(keys=["config_file_path"], desc="path to the configuration file", value=self._src_path)
        self.add_config(
            keys=["tox_root", "toxinidir"],
            of_type=Path,
            default=self._root,
            post_process=self._root.joinpath,  # a relative root is relative to the configuration file, not to cwd
            desc="the root directory (where the configuration file is found)",
        )
        self.add_constant("tox_root_name", "name of the root directory", self._root.name)
        self.add_config(
            keys=["package_root", "setupdir"],
            of_type=Path,
            default=self._default_package_root,
            post_process=self._relative_to_tox_root,
            desc="indicates where the packaging root file exists (historically setup.py file or pyproject.toml now)",
        )
        self.add_constant("home", "the user's home directory", Path.home)

        self.add_config(
            keys=["work_dir", "toxworkdir"],
            of_type=Path,
            default=self._default_work_dir,
            post_process=self._work_dir_post_process,
            desc="working directory",
        )
        self.add_config(
            keys=["temp_dir"],
            of_type=Path,
            default=self._default_temp_dir,
            post_process=self._relative_to_tox_root,
            desc="a folder for temporary files (is not cleaned at start)",
        )
        self.add_config(
            keys=["venv_redirect"],
            of_type=bool,
            default=None,
            desc="(provisional) point a PEP-832 .venv redirect file at a tox environment, so editors can discover it; "
            "unset means on unless a tox environment lives at .venv",
        )
        self.add_config(
            keys=["venv_redirect_env"],
            of_type=str,
            default=None,
            desc="(provisional) the tox environment the .venv redirect file points at, picked automatically when unset",
        )
        self.add_constant("host_python", "the host python executable path", sys.executable)

    def _default_package_root(self, _conf: Config, _env_name: str | None) -> Path:
        return self.get("tox_root", Path)

    def _relative_to_tox_root(self, folder: Path) -> Path:
        if not folder.is_absolute():
            folder = self.get("tox_root", Path) / folder
        return folder

    def _default_work_dir(  # override signature
        self,
        conf: Config,  # ruff:ignore[unused-method-argument]  # override signature
        env_name: str | None,  # ruff:ignore[unused-method-argument]  # override signature
    ) -> Path:
        return self.get("tox_root", Path) / ".tox"

    def _work_dir_post_process(self, folder: Path) -> Path:
        return self._conf.work_dir if self._conf.options.work_dir else self._relative_to_tox_root(folder)

    def _default_temp_dir(  # override signature
        self,
        conf: Config,  # ruff:ignore[unused-method-argument]  # override signature
        env_name: str | None,  # ruff:ignore[unused-method-argument]  # override signature
    ) -> Path:
        return self.get("work_dir", Path) / ".tmp"

    @override
    def _on_duplicate_conf(self, key: str, definition: ConfigDefinition[V]) -> None:
        pass  # core definitions may be defined multiple times as long as all their options match, first defined wins


class EnvConfigSet(ConfigSet):
    """Configuration set for a tox environment.

    :param conf: the global tox configuration
    :param section: the section that holds the environment settings
    :param env_name: the name of the tox environment

    :var default_set_env_loader: returns the ``set_env`` defaults of the environment
    :var exported_set_env_loader: returns the variables tox exports to the environment

    """

    def __init__(self, conf: Config, section: Section, env_name: str) -> None:
        super().__init__(conf, section, env_name)
        self.default_set_env_loader: Callable[[], Mapping[str, str]] = dict
        self.exported_set_env_loader: Callable[[], Mapping[str, Callable[[], str]]] = dict

    @override
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self._env_name!r}, loaders={self.loaders!r})"

    @override
    def register_config(self) -> None:
        def set_env_post_process(values: SetEnv) -> SetEnv:
            values.update(self.default_set_env_loader(), override=False)
            values.export({"PYTHONIOENCODING": lambda: "utf-8", **self.exported_set_env_loader()})
            return values

        def set_env_factory(raw: object) -> SetEnv:
            def is_valid_value(value: object) -> bool:
                if isinstance(value, SetEnvValue):
                    return True
                if isinstance(value, dict):
                    return "value" in value and isinstance(value.get("value"), SetEnvValue)
                return False

            if not (
                isinstance(raw, (str, SetEnvReference))
                or (isinstance(raw, dict) and all(isinstance(k, str) and is_valid_value(v) for k, v in raw.items()))
                or (
                    isinstance(raw, list)
                    and all(
                        isinstance(e, SetEnvReference)
                        or (isinstance(e, dict) and all(isinstance(k, str) and is_valid_value(v) for k, v in e.items()))
                        for e in raw
                    )
                )
            ):
                msg = (
                    f"set_env expected str, dict[str, str], or list[dict[str, str]], got {type(raw).__name__}: {raw!r}"
                )
                raise TypeError(msg)
            return SetEnv(cast("SetEnvRaw", raw), self.name, self.env_name, root)

        root = self._conf.core["tox_root"]
        self.add_config(
            keys=["set_env", "setenv"],
            of_type=SetEnv,
            factory=set_env_factory,
            default=SetEnv("", self.name, self.env_name, root),
            desc="environment variables to set when running commands in the tox environment",
            post_process=set_env_post_process,
        )

    def set_env_lines(self, chain: list[str]) -> str:
        # load first: a {env:...} in an environment file name reads this set_env, and the chain would reject that load
        """Get the ``set_env`` setting as lines, loading it first.

        :param chain: the chain of configuration keys the load belongs to

        :returns: the environment variables as ``KEY=VALUE`` lines

        """
        self.load("set_env", chain)
        loaded: Final[ConfigDynamicDefinition[SetEnv]] = cast(
            "ConfigDynamicDefinition[SetEnv]", self._defined["set_env"]
        )
        configured: Final[ConfigDynamicDefinition[SetEnv]] = ConfigDynamicDefinition(
            loaded.keys,
            loaded.desc,
            SetEnv,
            SetEnv("", self.name, self.env_name, self._conf.core["tox_root"]),
            factory=loaded.factory,
        )
        return configured(self._conf, self.loaders, ConfigLoadArgs(chain, self.name, self.env_name)).lines()


__all__ = [
    "ConfigSet",
    "CoreConfigSet",
    "EnvConfigSet",
]
