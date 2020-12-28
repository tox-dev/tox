import os
import sys
from abc import ABC, abstractmethod
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from threading import RLock
from typing import Any, Dict, Iterator, List, NoReturn, Optional, Sequence, Set, Tuple, Union, cast

from packaging.markers import Variable
from packaging.requirements import Requirement

from tox.config.cli.parser import Parsed
from tox.config.sets import ConfigSet
from tox.execute.api import ExecuteStatus
from tox.execute.pep517_backend import LocalSubProcessPep517Executor
from tox.execute.request import StdinSource
from tox.journal import EnvJournal
from tox.report import ToxHandler
from tox.tox_env.errors import Fail
from tox.tox_env.python.package import PythonPackage
from tox.util.pep517.frontend import BackendFailed, CmdStatus, ConfigSettings, Frontend, WheelResult

from ..api import VirtualEnv

if sys.version_info >= (3, 8):  # pragma: no cover (py38+)
    from importlib.metadata import Distribution, PathDistribution  # type: ignore[attr-defined]
else:  # pragma: no cover (<py38)
    from importlib_metadata import Distribution, PathDistribution  # noqa


TOX_PACKAGE_ENV_ID = "virtualenv-pep-517"


class PackageType(Enum):
    sdist = 1
    wheel = 2
    dev = 3
    skip = 4


class ToxCmdStatus(CmdStatus):
    def __init__(self, execute_status: ExecuteStatus) -> None:
        self._execute_status = execute_status

    @property
    def done(self) -> bool:
        # 1. process died
        status = self._execute_status
        if status.exit_code is not None:
            return True
        # 2. the backend output reported back that our command is done
        content = status.out
        at = content.rfind(b"Backend: Write response ")
        if at != -1 and content.find(b"\n", at) != -1:
            return True
        return False

    def out_err(self) -> Tuple[str, str]:
        status = self._execute_status
        if status is None or status.outcome is None:
            return "", ""
        return status.outcome.out_err()


class Pep517VirtualEnvPackage(VirtualEnv, PythonPackage, Frontend, ABC):
    """local file system python virtual environment via the virtualenv package"""

    def __init__(
        self, conf: ConfigSet, core: ConfigSet, options: Parsed, journal: EnvJournal, log_handler: ToxHandler
    ) -> None:
        VirtualEnv.__init__(self, conf, core, options, journal, log_handler)
        Frontend.__init__(self, *Frontend.create_args_from_folder(core["tox_root"]))
        self._distribution_meta: Optional[PathDistribution] = None  # type: ignore[no-any-unimported]
        self._build_requires: Optional[Tuple[Requirement]] = None
        self._build_wheel_cache: Optional[WheelResult] = None
        self._backend_executor: Optional[LocalSubProcessPep517Executor] = None
        self._package_dependencies: Optional[List[Requirement]] = None
        self._lock = RLock()  # can build only one package at a time
        self._package: Optional[Path] = None

    def register_config(self) -> None:
        super().register_config()
        self.conf.add_config(
            keys=["meta_dir"],
            of_type=Path,
            default=lambda conf, name: cast(Path, self.conf["env_dir"]) / ".meta",
            desc="directory assigned to the tox environment",
        )
        self.conf.add_config(
            keys=["pkg_dir"],
            of_type=Path,
            default=lambda conf, name: cast(Path, self.conf["env_dir"]) / "dist",
            desc="directory assigned to the tox environment",
        )

    @property
    def meta_folder(self) -> Path:
        meta_folder: Path = self.conf["meta_dir"]
        meta_folder.mkdir(exist_ok=True)
        return meta_folder

    def _ensure_meta_present(self) -> None:
        if self._distribution_meta is None:
            self.ensure_setup()
            dist_info = self.prepare_metadata_for_build_wheel(self.meta_folder).metadata
            self._distribution_meta = Distribution.at(str(dist_info))

    @abstractmethod
    def _build_artifact(self) -> Path:
        raise NotImplementedError

    def perform_packaging(self) -> List[Path]:
        """build_wheel/build_sdist"""
        with self._lock:
            if self._package is None:
                self.ensure_setup()
                self._package = self._build_artifact()
        return [self._package]

    def get_package_dependencies(self, extras: Optional[Set[str]] = None) -> List[Requirement]:
        with self._lock:
            if self._package_dependencies is None:
                self._package_dependencies = self._load_package_dependencies(extras)
        return self._package_dependencies

    def _load_package_dependencies(self, extras: Optional[Set[str]]) -> List[Requirement]:
        self._ensure_meta_present()
        if extras is None:
            extras = set()
        result: List[Requirement] = []
        if self._distribution_meta is None:
            raise RuntimeError
        requires = self._distribution_meta.requires or []
        for v in requires:
            req = Requirement(v)
            markers: List[Union[str, Tuple[Variable, Variable, Variable]]] = getattr(req.marker, "_markers", []) or []
            extra: Optional[str] = None
            _at: Optional[int] = None
            for _at, (m_key, op, m_val) in (
                (j, i) for j, i in enumerate(markers) if isinstance(i, tuple) and len(i) == 3
            ):
                if m_key.value == "extra" and op.value == "==":
                    extra = m_val.value
                    break
            if extra is None or extra in extras:
                if _at is not None:
                    del markers[_at]
                    _at -= 1
                    if _at > 0 and (isinstance(markers[_at], str) and markers[_at] in ("and", "or")):
                        del markers[_at]
                    if len(markers) == 0:
                        req.marker = None
                result.append(req)
        return result

    @property
    def backend_executor(self) -> LocalSubProcessPep517Executor:
        if self._backend_executor is None:
            self._backend_executor = LocalSubProcessPep517Executor(
                colored=self.options.is_colored,
                cmd=self.backend_cmd,
                env=self.environment_variables,
                cwd=self._root,
            )

        return self._backend_executor

    @property
    def pkg_dir(self) -> Path:
        return cast(Path, self.conf["pkg_dir"])

    @property
    def backend_cmd(self) -> Sequence[str]:
        return ["python"] + self.backend_args

    @property
    def environment_variables(self) -> Dict[str, str]:
        env = super().environment_variables
        env["PYTHONPATH"] = os.pathsep.join(str(i) for i in self._backend_paths)
        return env

    def teardown(self) -> None:
        if self._backend_executor is not None:
            self._send("_exit", None)
            self._backend_executor.close()

    @contextmanager
    def _send_msg(self, cmd: str, result_file: Path, msg: str) -> Iterator[CmdStatus]:
        with self.execute_async(
            cmd=self.backend_cmd,
            cwd=self._root,
            stdin=StdinSource.API,
            show=None,
            run_id=cmd,
            executor=self.backend_executor,
        ) as execute_status:
            execute_status.write_stdin(f"{msg}{os.linesep}")
            yield ToxCmdStatus(execute_status)
        outcome = execute_status.outcome
        if outcome is not None:
            outcome.assert_success()

    @contextmanager
    def _wheel_directory(self) -> Iterator[Path]:
        yield self.pkg_dir  # use our local wheel directory

    def build_wheel(
        self,
        wheel_directory: Path,
        config_settings: Optional[ConfigSettings] = None,
        metadata_directory: Optional[Path] = None,
    ) -> WheelResult:
        # only build once a wheel per session - might need more than once if the backend doesn't
        # support prepare metadata for wheel
        if self._build_wheel_cache is None:
            self._build_wheel_cache = super().build_wheel(wheel_directory, config_settings, metadata_directory)
        return self._build_wheel_cache

    def _send(self, cmd: str, missing: Any, **kwargs: Any) -> Tuple[Any, str, str]:
        try:
            return super()._send(cmd, missing, **kwargs)
        except BackendFailed as exception:
            raise Fail(exception)

    def _required_command_missing(self, cmd: str) -> NoReturn:
        try:
            super()._required_command_missing(cmd)
        except BackendFailed as exception:
            raise Fail(exception)

    def requires(self) -> Tuple[Requirement, ...]:
        return self._requires
