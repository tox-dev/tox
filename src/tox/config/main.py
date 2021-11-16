import os
from collections import OrderedDict, defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterator, List, Optional, Sequence, Tuple, Type, TypeVar

from tox.config.loader.api import Loader, OverrideMap

from ..session.common import CliEnv
from .loader.section import Section
from .sets import ConfigSet, CoreConfigSet, EnvConfigSet
from .source import Source

if TYPE_CHECKING:
    from .cli.parser import Parsed

T = TypeVar("T", bound=ConfigSet)


class Config:
    """Main configuration object for tox."""

    def __init__(
        self,
        config_source: Source,
        options: "Parsed",
        root: Path,
        pos_args: Optional[Sequence[str]],
        work_dir: Path,
    ) -> None:
        self._pos_args = None if pos_args is None else tuple(pos_args)
        self._work_dir = work_dir
        self._root = root
        self._options = options

        self._overrides: OverrideMap = defaultdict(list)
        for override in options.override:
            self._overrides[override.namespace].append(override)

        self._src = config_source
        self._key_to_conf_set: Dict[Tuple[str, str], ConfigSet] = OrderedDict()
        self._core_set: Optional[CoreConfigSet] = None

    def register_config_set(self, name: str, env_config_set: EnvConfigSet) -> None:  # noqa: U100
        raise NotImplementedError  # this should be overwritten by the state object before called

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

    def sections(self) -> Iterator[Section]:
        yield from self._src.sections()

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
            options=parsed,
            pos_args=pos_args,
            root=root,
            work_dir=work_dir,
        )

    @property
    def options(self) -> "Parsed":
        return self._options

    @property
    def core(self) -> CoreConfigSet:
        """:return: the core configuration"""
        if self._core_set is not None:
            return self._core_set
        core_section = self._src.get_core_section()
        core = CoreConfigSet(self, core_section, self._root, self.src_path)
        core.loaders.extend(self._src.get_loaders(core_section, base=[], override_map=self._overrides, conf=core))
        self._core_set = core
        from tox.plugin.manager import MANAGER

        MANAGER.tox_add_core_config(core, self)
        return core

    def get_section_config(
        self,
        section: Section,
        base: Optional[List[str]],
        of_type: Type[T],
        for_env: Optional[str],
        loaders: Optional[Sequence[Loader[Any]]] = None,
        initialize: Optional[Callable[[T], None]] = None,
    ) -> T:
        key = section.key, for_env or ""
        try:
            return self._key_to_conf_set[key]  # type: ignore[return-value] # expected T but found ConfigSet
        except KeyError:
            conf_set = of_type(self, section, for_env)
            self._key_to_conf_set[key] = conf_set
            for loader in self._src.get_loaders(section, base, self._overrides, conf_set):
                conf_set.loaders.append(loader)
            if loaders is not None:
                conf_set.loaders.extend(loaders)
            if initialize is not None:
                initialize(conf_set)
            return conf_set

    def get_env(
        self,
        item: str,
        package: bool = False,
        loaders: Optional[Sequence[Loader[Any]]] = None,
    ) -> EnvConfigSet:
        """
        Return the configuration for a given tox environment (will create if not exist yet).

        :param item: the name of the environment
        :param package: a flag indicating if the environment is of type packaging or not (only used for creation)
        :param loaders: loaders to use for this configuration (only used for creation)
        :return: the tox environments config
        """
        section, base = self._src.get_tox_env_section(item)
        conf_set = self.get_section_config(
            section,
            base=None if package else base,
            of_type=EnvConfigSet,
            for_env=item,
            loaders=loaders,
            initialize=lambda e: self.register_config_set(item, e),
        )
        from tox.plugin.manager import MANAGER

        MANAGER.tox_add_env_config(conf_set, self)
        return conf_set

    def env_list(self, everything: bool = False) -> Iterator[str]:
        """
        :param everything: if ``True`` returns all discovered tox environment names from the configuration

        :return: Return the tox environment names, by default only the default env list entries.
        """
        fallback_env = "py"
        use_env_list: Optional[CliEnv] = getattr(self._options, "env", None)
        if everything or (use_env_list is not None and use_env_list.all):
            _at = 0
            for _at, env in enumerate(self, start=1):
                yield env
            if _at == 0:  # if we discovered no other env, inject the default
                yield fallback_env
            return
        if use_env_list is not None and use_env_list.use_default_list:
            use_env_list = self.core["env_list"]
        if use_env_list is None or bool(use_env_list) is False:
            use_env_list = CliEnv([fallback_env])
        yield from use_env_list


___all__ = [
    "Config",
]
