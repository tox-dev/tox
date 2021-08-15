import os
from collections import OrderedDict, defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterator, List, Optional, Sequence, Tuple

from tox.config.loader.api import Loader, Override, OverrideMap

from .sets import CoreConfigSet, EnvConfigSet
from .source import Source

if TYPE_CHECKING:
    from .cli.parser import Parsed


class Config:
    """Main configuration object for tox."""

    def __init__(
        self,
        config_source: Source,
        overrides: List[Override],
        root: Path,
        pos_args: Optional[Sequence[str]],
        work_dir: Path,
    ) -> None:
        self._pos_args = None if pos_args is None else tuple(pos_args)
        self._work_dir = work_dir
        self._root = root

        self._overrides: OverrideMap = defaultdict(list)
        for override in overrides:
            self._overrides[override.namespace].append(override)

        self._src = config_source
        self._env_to_set: Dict[str, EnvConfigSet] = OrderedDict()
        self._core_set: Optional[CoreConfigSet] = None
        self.register_config_set: Callable[[str, EnvConfigSet], Any] = lambda n, e: None

    def pos_args(self, to_path: Optional[Path]) -> Optional[Tuple[str, ...]]:
        """
        :param to_path: if not None rewrite relative posargs paths from cwd to to_path
        :return: positional argument
        """
        if self._pos_args is not None and to_path is not None and Path.cwd() != to_path:
            args = []
            to_path_str = os.path.abspath(str(to_path))  # we use os.path to unroll .. in path without resolve
            for arg in self._pos_args:
                path_arg = Path(arg)
                if path_arg.exists() and not path_arg.is_absolute():
                    path_arg_str = os.path.abspath(str(path_arg))  # we use os.path to unroll .. in path without resolve
                    relative = os.path.relpath(path_arg_str, to_path_str)  # we use os.path to not fail when not within
                    args.append(relative)
                else:
                    args.append(arg)
            return tuple(args)
        return self._pos_args

    @property
    def work_dir(self) -> Path:
        """:return: working directory for this project"""
        return self._work_dir

    @property
    def src_path(self) -> Path:
        """:return: the location of the tox configuration source"""
        return self._src.path

    def __iter__(self) -> Iterator[str]:
        """:return: an iterator that goes through existing environments"""
        return self._src.envs(self.core)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(config_source={self._src!r})"

    def __contains__(self, item: str) -> bool:
        """:return: check if an environment already exists"""
        return any(name for name in self if name == item)

    @classmethod
    def make(cls, parsed: "Parsed", pos_args: Optional[Sequence[str]], source: Source) -> "Config":
        """Make a tox configuration object."""
        # root is the project root, where the configuration file is at
        # work dir is where we put our own files
        root: Path = source.path.parent if parsed.root_dir is None else parsed.root_dir
        work_dir: Path = source.path.parent if parsed.work_dir is None else parsed.work_dir
        return cls(
            config_source=source,
            overrides=parsed.override,
            pos_args=pos_args,
            root=root,
            work_dir=work_dir,
        )

    @property
    def core(self) -> CoreConfigSet:
        """:return: the core configuration"""
        if self._core_set is not None:
            return self._core_set
        core = CoreConfigSet(self, self._root)
        for loader in self._src.get_core(self._overrides):
            core.loaders.append(loader)

        from tox.plugin.manager import MANAGER

        MANAGER.tox_add_core_config(core)
        self._core_set = core
        return core

    def get_env(
        self, item: str, package: bool = False, loaders: Optional[Sequence[Loader[Any]]] = None
    ) -> EnvConfigSet:
        """
        Return the configuration for a given tox environment (will create if not exist yet).

        :param item: the name of the environment
        :param package: a flag indicating if the environment is of type packaging or not (only used for creation)
        :param loaders: loaders to use for this configuration (only used for creation)
        :return: the tox environments config
        """
        try:
            return self._env_to_set[item]
        except KeyError:
            env = EnvConfigSet(self, item)
            self._env_to_set[item] = env
            if loaders is not None:
                env.loaders.extend(loaders)
            for loader in self._src.get_env_loaders(item, self._overrides, package, env):
                env.loaders.append(loader)
            # whenever we load a new configuration we need to build a tox environment which process defines the valid
            # configuration values
            self.register_config_set(item, env)
            return env
