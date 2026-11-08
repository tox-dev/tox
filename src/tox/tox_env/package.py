"""A tox environment that can build packages."""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import nullcontext
from pathlib import Path
from threading import RLock
from types import MethodType
from typing import TYPE_CHECKING, Any, Final, ParamSpec, TypeVar

from filelock import BaseFileLock, FileLock

from tox.util.path import ensure_private_dir
from tox.util.typing_compat import override

from .api import ToxEnv, ToxEnvCreateArgs

_P = ParamSpec("_P")
_R = TypeVar("_R")

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterator

    from tox.config.main import Config
    from tox.config.sets import EnvConfigSet

    from .runner import RunToxEnv


class Package:
    """package."""


class PathPackage(Package):
    """A package given by a path on the local file system.

    :param path: the path of the package

    """

    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path

    @override
    def __str__(self) -> str:
        return str(self.path)


class PackageToxEnv(ToxEnv, ABC):
    """The base of the tox environments that build a package to install into the run environments.

    :param create_args: the arguments the environment is created with

    """

    def __init__(self, create_args: ToxEnvCreateArgs) -> None:
        self._thread_lock = RLock()
        self._file_lock: BaseFileLock | None = None
        super().__init__(create_args)
        self._envs: set[str] = set()

    @override
    def __getattribute__(self, name: str) -> Any:  # simplint: ignore[SMP602]  # attribute lookup returns any attribute
        # the packaging class might be used by multiple environments in parallel, hold a lock for operations on it
        obj = object.__getattribute__(self, name)
        if isinstance(obj, MethodType):
            obj = PackageToxEnv._lock_method(self._thread_lock, self._file_lock, obj)
        return obj

    @staticmethod
    def _lock_method(thread_lock: RLock, file_lock: BaseFileLock | None, meth: Callable[_P, _R]) -> Callable[_P, _R]:
        def _func(*args: _P.args, **kwargs: _P.kwargs) -> _R:
            # A pre-existing package environment link must not redirect the lock file.
            with (
                thread_lock,
                file_lock
                if file_lock is not None
                and file_lock.is_locked is False
                and not Path(file_lock.lock_file).parent.is_symlink()
                else nullcontext(),
            ):
                return meth(*args, **kwargs)

        return _func

    @override
    def register_config(self) -> None:
        super().register_config()
        env_dir: Final[Path] = self.conf.get("env_dir", Path)
        self._file_lock = FileLock(env_dir / "file.lock")
        if not env_dir.is_symlink():
            ensure_private_dir(env_dir)
        self.conf.add_config(
            keys=["package_root", "setupdir"],
            of_type=Path,
            default=self.core.get("package_root", Path),
            post_process=self._relative_to_tox_root,
            desc="indicates where the packaging root file exists (historically setup.py file or pyproject.toml now)",
        )

    @override
    def _recreate_default(self, conf: Config, value: str | None) -> bool:
        return self.options.no_recreate_pkg is False and super()._recreate_default(conf, value)

    @abstractmethod
    def perform_packaging(self, for_env: EnvConfigSet) -> list[Package]:
        """Build the packages of the environment.

        :param for_env: the configuration of the run environment the packages are for

        :returns: the packages that were built

        """
        raise NotImplementedError

    # base hook, subclasses override it
    def register_run_env(self, run_env: RunToxEnv) -> Generator[tuple[str, str], PackageToxEnv, None]:  # ruff:ignore[unused-method-argument, no-self-use]
        """Register a run environment that uses the packages of this environment.

        :param run_env: the run environment

        :yields: the package types and the names of the run environment settings the packages are read from

        """
        return  # empty generator by default
        yield ("", "")  # unreachable, exists to establish yield type

    def mark_active_run_env(self, run_env: RunToxEnv) -> None:
        """Mark a run environment as active, so the packages are kept until it is torn down.

        :param run_env: the run environment

        """
        self._envs.add(run_env.conf.name)

    def teardown_env(self, conf: EnvConfigSet) -> None:
        """Tear the packaging environment down, once no run environment uses it.

        :param conf: the configuration of the run environment that is torn down

        """
        if conf.name in self._envs:
            # conf.name (".tox") may be missing in self._envs in the case of an automatically provisioned environment
            self._envs.remove(conf.name)
        if len(self._envs) == 0:
            self._teardown()

    @abstractmethod
    def child_pkg_envs(self, run_conf: EnvConfigSet) -> Iterator[PackageToxEnv]:
        """Get the packaging environments the packaging environment of a run environment depends on.

        :param run_conf: the configuration of the run environment

        :returns: the packaging environments

        """
        raise NotImplementedError


__all__ = [
    "Package",
    "PackageToxEnv",
    "PathPackage",
]
