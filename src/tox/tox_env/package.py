"""A tox environment that can build packages."""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import nullcontext
from pathlib import Path
from threading import RLock
from types import MethodType
from typing import TYPE_CHECKING, Any, Final, ParamSpec, TypeVar

from filelock import BaseFileLock, FileLock

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
    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path

    @override
    def __str__(self) -> str:
        return str(self.path)


class PackageToxEnv(ToxEnv, ABC):
    def __init__(self, create_args: ToxEnvCreateArgs) -> None:
        self._thread_lock = RLock()
        self._file_lock: BaseFileLock | None = None
        super().__init__(create_args)
        self._envs: set[str] = set()

    @override
    def __getattribute__(self, name: str) -> Any:
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
            env_dir.mkdir(parents=True, exist_ok=True)
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
        raise NotImplementedError

    def register_run_env(self, run_env: RunToxEnv) -> Generator[tuple[str, str], PackageToxEnv, None]:  # ruff:ignore[unused-method-argument, no-self-use]
        return  # empty generator by default
        yield ("", "")  # unreachable, exists to establish yield type

    def mark_active_run_env(self, run_env: RunToxEnv) -> None:
        self._envs.add(run_env.conf.name)

    def teardown_env(self, conf: EnvConfigSet) -> None:
        if conf.name in self._envs:
            # conf.name (".tox") may be missing in self._envs in the case of an automatically provisioned environment
            self._envs.remove(conf.name)
        if len(self._envs) == 0:
            self._teardown()

    @abstractmethod
    def child_pkg_envs(self, run_conf: EnvConfigSet) -> Iterator[PackageToxEnv]:
        raise NotImplementedError


__all__ = [
    "Package",
    "PackageToxEnv",
    "PathPackage",
]
