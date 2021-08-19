import os
import sys
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from threading import RLock
from typing import Any, Dict, Iterator, List, NoReturn, Optional, Sequence, Set, Tuple, Union, cast

from cachetools import cached
from packaging.markers import Variable
from packaging.requirements import Requirement

from tox.config.sets import EnvConfigSet
from tox.execute.api import ExecuteStatus
from tox.execute.pep517_backend import LocalSubProcessPep517Executor
from tox.execute.request import StdinSource
from tox.plugin import impl
from tox.tox_env.api import ToxEnvCreateArgs
from tox.tox_env.errors import Fail
from tox.tox_env.package import Package
from tox.tox_env.python.package import DevLegacyPackage, PythonPackageToxEnv, SdistPackage, WheelPackage
from tox.tox_env.register import ToxEnvRegister
from tox.util.pep517.frontend import BackendFailed, CmdStatus, ConfigSettings, Frontend

from ..api import VirtualEnv

if sys.version_info >= (3, 8):  # pragma: no cover (py38+)
    from importlib.metadata import Distribution, PathDistribution  # type: ignore[attr-defined]
else:  # pragma: no cover (<py38)
    from importlib_metadata import Distribution, PathDistribution  # noqa


TOX_PACKAGE_ENV_ID = "virtualenv-pep-517"


class ToxBackendFailed(Fail, BackendFailed):
    def __init__(self, backend_failed: BackendFailed) -> None:
        Fail.__init__(self)
        result: Dict[str, Any] = {
            "code": backend_failed.code,
            "exc_type": backend_failed.exc_type,
            "exc_msg": backend_failed.exc_msg,
        }
        BackendFailed.__init__(
            self,
            result,
            backend_failed.out,
            backend_failed.err,
        )


class ToxCmdStatus(CmdStatus):
    def __init__(self, execute_status: ExecuteStatus) -> None:
        self._execute_status = execute_status

    @property
    def done(self) -> bool:
        # 1. process died
        status = self._execute_status
        if status.exit_code is not None:  # pragma: no branch
            return True  # pragma: no cover
        # 2. the backend output reported back that our command is done
        return b"\n" in status.out.rpartition(b"Backend: Wrote response ")[0]

    def out_err(self) -> Tuple[str, str]:
        status = self._execute_status
        if status is None or status.outcome is None:  # interrupt before status create # pragma: no branch
            return "", ""  # pragma: no cover
        return status.outcome.out_err()


class Pep517VirtualEnvPackage(PythonPackageToxEnv, VirtualEnv, Frontend):
    """local file system python virtual environment via the virtualenv package"""

    def __init__(self, create_args: ToxEnvCreateArgs) -> None:
        VirtualEnv.__init__(self, create_args)
        root: Path = self.conf["package_root"]
        Frontend.__init__(self, *Frontend.create_args_from_folder(root))

        self._backend_executor_: Optional[LocalSubProcessPep517Executor] = None
        self._builds: Set[str] = set()
        self._distribution_meta: Optional[PathDistribution] = None
        self._package_dependencies: Optional[List[Requirement]] = None
        self._pkg_lock = RLock()  # can build only one package at a time
        into: Dict[str, Any] = {}
        pkg_cache = cached(into, key=lambda *args, **kwargs: "wheel" if "wheel_directory" in kwargs else "sdist")
        self.build_wheel = pkg_cache(self.build_wheel)  # type: ignore
        self.build_sdist = pkg_cache(self.build_sdist)  # type: ignore

    @staticmethod
    def id() -> str:
        return "virtualenv-pep-517"

    def register_config(self) -> None:
        super().register_config()
        self.conf.add_config(
            keys=["meta_dir"],
            of_type=Path,
            default=lambda conf, name: self.env_dir / ".meta",
            desc="directory where to put the project metadata files",
        )
        self.conf.add_config(
            keys=["pkg_dir"],
            of_type=Path,
            default=lambda conf, name: self.env_dir / "dist",
            desc="directory where to put project packages",
        )

    @property
    def pkg_dir(self) -> Path:
        return cast(Path, self.conf["pkg_dir"])

    @property
    def meta_folder(self) -> Path:
        meta_folder: Path = self.conf["meta_dir"]
        meta_folder.mkdir(exist_ok=True)
        return meta_folder

    def notify_of_run_env(self, conf: EnvConfigSet) -> None:
        super().notify_of_run_env(conf)
        self._builds.add(conf["package"])

    def _setup_env(self) -> None:
        super()._setup_env()
        if "wheel" in self._builds:
            build_requires = self.get_requires_for_build_wheel().requires
            self.installer.install(build_requires, PythonPackageToxEnv.__name__, "requires_for_build_wheel")
        if "sdist" in self._builds:
            build_requires = self.get_requires_for_build_sdist().requires
            self.installer.install(build_requires, PythonPackageToxEnv.__name__, "requires_for_build_sdist")

    def _teardown(self) -> None:
        if self._backend_executor_ is not None:
            try:
                if self._backend_executor.is_alive:
                    self._send("_exit")  # try first on amicable shutdown
            except SystemExit:  # if already has been interrupted ignore
                pass
            finally:
                self._backend_executor_.close()
        super()._teardown()

    def perform_packaging(self, for_env: EnvConfigSet) -> List[Package]:
        """build the package to install"""
        of_type: str = for_env["package"]
        extras: Set[str] = for_env["extras"]
        deps = self._dependencies_with_extras(self._get_package_dependencies(), extras)
        if of_type == "dev-legacy":
            deps = [*self.requires(), *self.get_requires_for_build_sdist().requires] + deps
            package: Package = DevLegacyPackage(self.core["tox_root"], deps)  # the folder itself is the package
        elif of_type == "sdist":
            with self._pkg_lock:
                package = SdistPackage(self.build_sdist(sdist_directory=self.pkg_dir).sdist, deps)
        elif of_type == "wheel":
            with self._pkg_lock:
                path = self.build_wheel(
                    wheel_directory=self.pkg_dir,
                    metadata_directory=self.meta_folder,
                    config_settings=self._wheel_config_settings,
                ).wheel
            package = WheelPackage(path, deps)
        else:  # pragma: no cover # for when we introduce new packaging types and don't implement
            raise TypeError(f"cannot handle package type {of_type}")  # pragma: no cover
        return [package]

    def _get_package_dependencies(self) -> List[Requirement]:
        with self._pkg_lock:
            if self._package_dependencies is None:  # pragma: no branch
                self._ensure_meta_present()
                requires: List[str] = cast(PathDistribution, self._distribution_meta).requires or []
                self._package_dependencies = [Requirement(i) for i in requires]
        return self._package_dependencies

    def _ensure_meta_present(self) -> None:
        if self._distribution_meta is not None:  # pragma: no branch
            return  # pragma: no cover
        self.setup()
        dist_info = self.prepare_metadata_for_build_wheel(self.meta_folder, self._wheel_config_settings).metadata
        self._distribution_meta = Distribution.at(str(dist_info))  # type: ignore[no-untyped-call]

    @staticmethod
    def _dependencies_with_extras(deps: List[Requirement], extras: Set[str]) -> List[Requirement]:
        result: List[Requirement] = []
        for req in deps:
            req = deepcopy(req)
            markers: List[Union[str, Tuple[Variable, Variable, Variable]]] = getattr(req.marker, "_markers", []) or []
            # find the extra marker (if has)
            _at: Optional[int] = None
            extra: Optional[str] = None
            for _at, (marker_key, op, marker_value) in (
                (_at_marker, marker)
                for _at_marker, marker in enumerate(markers)
                if isinstance(marker, tuple) and len(marker) == 3
            ):
                if marker_key.value == "extra" and op.value == "==":  # pragma: no branch
                    extra = marker_value.value
                    del markers[_at]
                    _at -= 1
                    if _at > 0 and (isinstance(markers[_at], str) and markers[_at] in ("and", "or")):
                        del markers[_at]
                    if len(markers) == 0:
                        req.marker = None
                    break
            if not (extra is None or extra in extras):
                continue
            result.append(req)
        return result

    @contextmanager
    def _wheel_directory(self) -> Iterator[Path]:
        yield self.pkg_dir  # use our local wheel directory for building wheel

    @property
    def _wheel_config_settings(self) -> Optional[ConfigSettings]:
        return {"--global-option": ["--bdist-dir", str(self.env_dir / "build")]}

    @property
    def _backend_executor(self) -> LocalSubProcessPep517Executor:
        if self._backend_executor_ is None:
            self._backend_executor_ = LocalSubProcessPep517Executor(
                colored=self.options.is_colored,
                cmd=self.backend_cmd,
                env=self._environment_variables,
                cwd=self._root,
            )

        return self._backend_executor_

    @property
    def backend_cmd(self) -> Sequence[str]:
        return ["python"] + self.backend_args

    @property
    def _environment_variables(self) -> Dict[str, str]:
        env = super()._environment_variables
        backend = os.pathsep.join(str(i) for i in self._backend_paths).strip()
        if backend:
            env["PYTHONPATH"] = backend
        return env

    @contextmanager
    def _send_msg(
        self, cmd: str, result_file: Path, msg: str  # noqa: U100
    ) -> Iterator[ToxCmdStatus]:  # type: ignore[override]
        with self.execute_async(
            cmd=self.backend_cmd,
            cwd=self._root,
            stdin=StdinSource.API,
            show=None,
            run_id=cmd,
            executor=self._backend_executor,
        ) as execute_status:
            execute_status.write_stdin(f"{msg}{os.linesep}")
            yield ToxCmdStatus(execute_status)
        outcome = execute_status.outcome
        if outcome is not None:  # pragma: no branch
            outcome.assert_success()

    def _send(self, cmd: str, **kwargs: Any) -> Tuple[Any, str, str]:
        try:
            if cmd == "prepare_metadata_for_build_wheel":
                # given we'll build a wheel we might skip the prepare step
                if "wheel" in self._builds:
                    result = {
                        "code": 1,
                        "exc_type": "AvoidRedundant",
                        "exc_msg": "will need to build wheel either way, avoid prepare",
                    }
                    raise BackendFailed(result, "", "")
            return super()._send(cmd, **kwargs)
        except BackendFailed as exception:
            raise exception if isinstance(exception, ToxBackendFailed) else ToxBackendFailed(exception) from exception

    def _unexpected_response(self, cmd: str, got: Any, expected_type: Any, out: str, err: str) -> NoReturn:
        try:
            super()._unexpected_response(cmd, got, expected_type, out, err)
        except BackendFailed as exception:
            raise exception if isinstance(exception, ToxBackendFailed) else ToxBackendFailed(exception) from exception

    def requires(self) -> Tuple[Requirement, ...]:
        return self._requires


@impl
def tox_register_tox_env(register: ToxEnvRegister) -> None:
    register.add_package_env(Pep517VirtualEnvPackage)
