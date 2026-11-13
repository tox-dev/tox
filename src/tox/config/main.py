from __future__ import annotations

import logging
import os
import sys
from collections import OrderedDict, defaultdict
from itertools import chain, tee
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, TypeVar, cast

from tox.util.redact import redact_argv
from tox.util.typing_compat import override

from .sets import ConfigSet, CoreConfigSet, EnvConfigSet
from .source.api import FactorLabelSource

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence

    from .cli.parser import Parsed
    from .loader.api import Loader, OverrideMap
    from .loader.memory import MemoryLoader
    from .loader.section import Section
    from .source import Source
    from .types import FactorGroup


T = TypeVar("T", bound=ConfigSet)
"""Type variable bound to the configuration set classes."""


class Config:
    """Main configuration object for tox.

    :param config_source: the source the configuration is read from
    :param options: the parsed command line options
    :param root: the project root directory, where the configuration file is
    :param pos_args: the positional arguments passed after ``--``
    :param work_dir: the directory where tox keeps its own files
    :param extra_envs: the environments to add to the configured ones

    :var memory_seed_loaders: the in-memory loaders that seed the environments by name

    """

    def __init__(  # ruff:ignore[too-many-arguments]  # <- no way around many args
        self,
        config_source: Source,
        options: Parsed,
        root: Path,
        pos_args: Sequence[str] | None,
        work_dir: Path,
        extra_envs: Iterable[str],
    ) -> None:
        self._pos_args = None if pos_args is None else tuple(pos_args)
        self._work_dir = work_dir
        self._root = root
        self._options = options
        self._extra_envs = extra_envs

        self._overrides: OverrideMap = defaultdict(list)
        for entry in options.override:
            self._overrides[entry.namespace].append(entry)

        self._src = config_source
        self._key_to_conf_set: dict[tuple[str, str, str], ConfigSet] = OrderedDict()
        self._env_to_conf_set: dict[str, EnvConfigSet] = {}
        self._core_set: CoreConfigSet | None = None
        self.memory_seed_loaders: defaultdict[str, list[MemoryLoader]] = defaultdict(list)

    @classmethod
    def make(cls, parsed: Parsed, pos_args: Sequence[str] | None, source: Source, extra_envs: Iterable[str]) -> Config:
        """Make a tox configuration object.

        :param parsed: the parsed command line options
        :param pos_args: the positional arguments passed after ``--``
        :param source: the source the configuration is read from
        :param extra_envs: the environments to add to the configured ones

        :returns: the configuration object

        """
        # root is the project root, where the configuration file is at
        # work dir is where we put our own files
        root: Path = source.path.parent if parsed.root_dir is None else parsed.root_dir
        work_dir: Path = source.path.parent if parsed.work_dir is None else parsed.work_dir
        # if these are relative we need to expand them them to ensure paths built on this can resolve independent on cwd
        root = root.resolve()
        work_dir = work_dir.resolve()
        return cls(
            config_source=source,
            options=parsed,
            pos_args=pos_args,
            root=root,
            work_dir=work_dir,
            extra_envs=extra_envs,
        )

    def __iter__(self) -> Iterator[str]:
        """:returns: an iterator that goes through existing environments"""
        # NOTE: `tee(self._extra_envs)[1]` is necessary for compatibility with
        # NOTE: Python 3.11 and older versions. Once Python 3.12 is the lowest
        # NOTE: supported version, it can be changed to
        # NOTE: `chain.from_iterable(tee(self._extra_envs, 1))`.
        return chain(self._src.envs(self.core), tee(self._extra_envs)[1])

    @property
    def core(self) -> CoreConfigSet:
        """The core configuration, loaded on first access."""
        if self._core_set is not None:
            return self._core_set
        core_section = self._src.get_core_section()
        core = CoreConfigSet(self, core_section, self._root, self.src_path)
        core.loaders.extend(self._src.get_loaders(core_section, base=[], override_map=self._overrides, conf=core))
        self._core_set = core
        return core

    @property
    def src_path(self) -> Path:
        """The location of the tox configuration source."""
        return self._src.path

    @override
    def __repr__(self) -> str:
        return f"{type(self).__name__}(config_source={self._src!r})"

    def __contains__(self, item: str) -> bool:
        """Check if an environment already exists.

        :param item: the name of the environment to look for

        :returns: whether an environment with that name is defined

        """
        return any(name == item for name in self)

    @property
    def work_dir(self) -> Path:
        """The working directory for this project."""
        return self._work_dir

    @property
    def options(self) -> Parsed:
        """The parsed command line options."""
        return self._options

    @property
    def overrides(self) -> OverrideMap:
        """The configuration overrides keyed by their target namespace."""
        return self._overrides

    def pos_args(self, to_path: Path | None, *, program_first: bool = False) -> tuple[str, ...] | None:
        """Get the positional arguments passed after ``--``, with path arguments made relative to a directory.

        :param to_path: the directory the path arguments are made relative to, ``None`` to keep them as they are
        :param program_first: whether the program comes before the positional arguments

        :returns: the positional arguments, or ``None`` when none were passed

        """
        if self._pos_args is not None and to_path is not None and Path.cwd() != to_path:
            # Windows resolves parent segments before following directory links.
            if sys.platform == "win32":
                to_path_str = os.path.abspath(str(to_path))  # ruff:ignore[os-path-abspath]  # path as written
            else:
                to_path_str = os.path.realpath(to_path)
            return tuple(
                self._rewrite_pos_arg(index, arg, to_path_str, program_first=program_first)
                for index, arg in enumerate(self._pos_args)
            )
        return self._pos_args

    @staticmethod
    def _rewrite_pos_arg(index: int, arg: str, to_path_str: str, *, program_first: bool) -> str:
        if not arg:
            return arg
        path_arg = Path(arg)
        is_existing_path = Config._is_existing_path(path_arg, arg)
        # A wrapper can run the first positional value as a program without tox knowing that it does.
        bare_first_value: bool = is_existing_path and index == 0 and path_arg.name == arg
        executable_file: bool = (
            bare_first_value
            and path_arg.is_file()
            and os.access(path_arg, os.X_OK)
            and (os.name != "nt" or path_arg.suffix.lower() in {".bat", ".cmd", ".com", ".exe"})
        )
        if bare_first_value and (program_first or executable_file):
            return arg
        if is_existing_path and not path_arg.is_absolute():
            return Config._rewrite_relative_path(arg, to_path_str)
        return arg

    @staticmethod
    def _is_existing_path(path_arg: Path, arg: str) -> bool:
        try:
            return path_arg.exists()
        except OSError:
            logging.debug("could not check if %r is an existing path", redact_argv([arg])[0])
            return False

    @staticmethod
    def _rewrite_relative_path(arg: str, to_path_str: str) -> str:
        # Preserve symlink spelling when normalizing parent segments.
        path_arg_str: Final[str] = os.path.abspath(arg)  # ruff:ignore[os-path-abspath]
        try:
            relative: Final[str] = os.path.relpath(path_arg_str, to_path_str)
        except ValueError:  # on Windows, relpath fails across drives (e.g. subst mounts)
            return path_arg_str
        if relative.startswith("-") and not arg.startswith("-"):
            return f"{os.curdir}{os.sep}{relative}"
        return relative

    def sections(self) -> Iterator[Section]:
        """Iterate over the sections of the configuration source.

        :yields: the sections, in the order the source defines them

        """
        yield from self._src.sections()

    def factor_labels(self, env_name: str | None) -> dict[str, FactorGroup]:
        """Get the factor labels defined for an environment.

        :param env_name: the environment name, ``None`` for the core configuration

        :returns: the factor labels, empty when the source does not define factor labels

        """
        return self._src.factor_labels(env_name) if isinstance(self._src, FactorLabelSource) else {}

    def get_env(
        self,
        item: str,
        # keeps the existing signature
        package: bool = False,  # ruff:ignore[boolean-type-hint-positional-argument, boolean-default-value-positional-argument]
        loaders: Sequence[Loader[Any]]  # simplint: ignore[imprecise-annotation]  # loaders read raw values of any type
        | None = None,
    ) -> EnvConfigSet:
        """Return the configuration for a given tox environment (will create if not exist yet).

        :param item: the name of the environment is
        :param package: a flag indicating if the environment is of type packaging or not (only used for creation)
        :param loaders: loaders to use for this configuration (only used for creation)

        :returns: the tox environments config

        """
        if item in self._env_to_conf_set:
            return self._env_to_conf_set[item]
        section, base_test, base_pkg = self._src.get_tox_env_section(item)
        result = self.get_section_config(
            section,
            base=base_pkg if package else base_test,
            of_type=EnvConfigSet,
            for_env=item,
            loaders=loaders,
        )
        self._env_to_conf_set[item] = result
        return result

    def get_section_config(
        self,
        section: Section,
        base: list[str] | None,
        of_type: type[T],
        for_env: str | None,
        loaders: Sequence[Loader[Any]]  # simplint: ignore[imprecise-annotation]  # loaders read raw values of any type
        | None = None,
    ) -> T:
        """Get the configuration set of a section, creating and caching it on first use.

        :param section: the section to load
        :param base: the base sections the configuration inherits from
        :param of_type: the configuration set type to create
        :param for_env: the environment name, ``None`` for the core configuration
        :param loaders: extra loaders to read values from, appended after the source loaders

        :returns: the configuration set of the section

        """
        key = section.key, for_env or "", "-".join(base or [])
        try:
            return cast("T", self._key_to_conf_set[key])
        except KeyError:
            conf_set = of_type(self, section, for_env)
            self._key_to_conf_set[key] = conf_set
            if for_env is not None:
                conf_set.loaders.extend(self.memory_seed_loaders.get(for_env, []))
            for loader in self._src.get_loaders(section, base, self._overrides, conf_set):
                conf_set.loaders.append(loader)
            if loaders is not None:
                conf_set.loaders.extend(loaders)
            return conf_set

    def clear_env(self, name: str) -> None:
        """Forget the configuration loaded for an environment, so it is loaded again when next used.

        :param name: the name of the environment

        """
        section, _, __ = self._src.get_tox_env_section(name)
        self._key_to_conf_set = {
            k: v for k, v in self._key_to_conf_set.items() if not (k[0] == section.key and k[1] == name)
        }
        self._env_to_conf_set.pop(name, None)


__all__ = [
    "Config",
]
