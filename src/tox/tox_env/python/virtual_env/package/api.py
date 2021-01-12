import os
import sys
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from threading import RLock
from typing import Any, Dict, Generator, Iterator, List, NoReturn, Optional, Sequence, Set, Tuple, Union, cast

from packaging.markers import Variable
from packaging.requirements import Requirement

from tox.config.cli.parser import Parsed
from tox.config.sets import CoreConfigSet, EnvConfigSet
from tox.execute.api import ExecuteStatus
from tox.execute.pep517_backend import LocalSubProcessPep517Executor
from tox.execute.request import StdinSource
from tox.journal import EnvJournal
from tox.plugin.impl import impl
from tox.report import ToxHandler
from tox.tox_env.errors import Fail
from tox.tox_env.package import PackageToxEnv
from tox.tox_env.python.api import PythonDep
from tox.tox_env.python.package import PythonPackage
from tox.tox_env.register import ToxEnvRegister
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
        content = status.out
        at = content.rfind(b"Backend: Wrote response ")
        if at != -1 and content.find(b"\n", at) != -1:
            return True
        return False

    def out_err(self) -> Tuple[str, str]:
        status = self._execute_status
        if status is None or status.outcome is None:  # interrupt before status create # pragma: no branch
            return "", ""  # pragma: no cover
        return status.outcome.out_err()


class Pep517VirtualEnvPackage(VirtualEnv, PythonPackage, Frontend):
    """local file system python virtual environment via the virtualenv package"""

    def __init__(
        self, conf: EnvConfigSet, core: CoreConfigSet, options: Parsed, journal: EnvJournal, log_handler: ToxHandler
    ) -> None:
        VirtualEnv.__init__(self, conf, core, options, journal, log_handler)
        Frontend.__init__(self, *Frontend.create_args_from_folder(core["tox_root"]))
        self._distribution_meta: Optional[PathDistribution] = None  # type: ignore[no-any-unimported]
        self._build_requires: Optional[Tuple[Requirement]] = None
        self._build_wheel_cache: Optional[WheelResult] = None
        self._backend_executor: Optional[LocalSubProcessPep517Executor] = None
        self._package_dependencies: Optional[List[Requirement]] = None
        self._lock = RLock()  # can build only one package at a time
        self._package: Dict[Tuple[PackageType, str], Any] = {}
        self._run_env_to_wheel_builder_env: Dict[str, PackageToxEnv] = {}
        self._run_env_to_info: Dict[str, Tuple[PackageType, str]] = {}
        self._teardown_done = False

    @staticmethod
    def id() -> str:
        return "virtualenv-pep-517"

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

    def setup(self) -> None:
        super().setup()
        build_requires = [PythonDep(i) for i in self.get_requires_for_build_wheel().requires]
        self.cached_install(build_requires, PythonPackage.__name__, "requires_for_build_wheel")

    @property
    def meta_folder(self) -> Path:
        meta_folder: Path = self.conf["meta_dir"]
        meta_folder.mkdir(exist_ok=True)
        return meta_folder

    def _ensure_meta_present(self) -> None:
        if self._distribution_meta is not None:  # pragma: no branch
            return  # pragma: no cover
        self.ensure_setup()
        dist_info = self.prepare_metadata_for_build_wheel(self.meta_folder).metadata
        self._distribution_meta = Distribution.at(str(dist_info))  # type: ignore[no-untyped-call]

    def perform_packaging(self, name: str) -> List[Path]:
        """build the package to install"""
        content = self._run_env_to_info[name]
        if content in self._package:
            path: Path = self._package[content]
        else:
            pkg_type, build_env = content
            if pkg_type is PackageType.dev:
                path = self.core["tox_root"]  # the folder itself is the package
            elif (pkg_type is PackageType.sdist) or (pkg_type is PackageType.wheel and build_env == self.conf.name):
                with self._lock:
                    self.ensure_setup()
                    if pkg_type is PackageType.sdist:
                        build_requires = [PythonDep(i) for i in self.get_requires_for_build_sdist().requires]
                        self.cached_install(build_requires, PythonPackage.__name__, "requires_for_build_sdist")
                        path = self.build_sdist(sdist_directory=self.pkg_dir).sdist
                    else:
                        path = self.build_wheel(
                            wheel_directory=self.pkg_dir,
                            metadata_directory=self.meta_folder,
                            config_settings={"--global-option": ["--bdist-dir", str(self.conf["env_dir"] / "build")]},
                        ).wheel
            elif pkg_type is PackageType.wheel:
                wheel_pkg_env = self._run_env_to_wheel_builder_env[build_env]
                with wheel_pkg_env.display_context(suspend=self.has_display_suspended):
                    wheel_pkg_env.ref_count.increment()
                    try:
                        path = wheel_pkg_env.perform_packaging(name)[0]
                    finally:
                        wheel_pkg_env.teardown()
            else:  # pragma: no cover # for when we introduce new packaging types and don't implement
                raise TypeError(f"cannot handle package type {pkg_type}")  # pragma: no cover
            self._package[content] = path
        return [path]

    def create_package_env(self, name: str, info: Tuple[Any, ...]) -> Generator[Tuple[str, str], "PackageToxEnv", None]:
        if not (  # pragma: no branch
            isinstance(info, tuple)
            and len(info) == 2
            and isinstance(info[0], PackageType)
            and isinstance(info[1], str)  # ensure we can handle package info
        ):
            raise ValueError(f"{name} package info {info} is invalid by {self.conf.name}")  # pragma: no cover

        pkg_type, wheel_build_env = info[0], info[1]
        self._run_env_to_info[name] = pkg_type, wheel_build_env

        if pkg_type is not PackageType.wheel or wheel_build_env == self.conf.name:
            return

        yield  # type: ignore[misc]
        wheel_pkg_tox_env = yield wheel_build_env, self.id()
        if isinstance(wheel_pkg_tox_env, Pep517VirtualEnvPackage):  # pragma: no branch
            wheel_pkg_tox_env._run_env_to_info[name] = PackageType.wheel, wheel_build_env
        self._run_env_to_wheel_builder_env[wheel_build_env] = wheel_pkg_tox_env

    def package_envs(self, name: str) -> Generator["PackageToxEnv", None, None]:
        yield from super().package_envs(name)
        if name in self._run_env_to_info:
            _, env = self._run_env_to_info[name]
            if env is not None and env != self.conf.name:
                yield self._run_env_to_wheel_builder_env[env]

    def get_package_dependencies(self, for_env: EnvConfigSet) -> List[Requirement]:
        env_name = for_env.name
        extras: Set[str] = for_env["extras"]
        with self._lock:
            if self._package_dependencies is None:  # pragma: no branch
                self._ensure_meta_present()
                dependencies: List[Requirement] = []
                of_type, _ = self._run_env_to_info[env_name]
                if of_type == PackageType.dev:
                    dependencies.extend(self.requires())
                    dependencies.extend(self.get_requires_for_build_sdist().requires)
                dependencies.extend(self.discover_package_dependencies(self._distribution_meta, extras))
                self._package_dependencies = dependencies
        return self._package_dependencies

    @staticmethod
    def discover_package_dependencies(  # type: ignore[no-any-unimported]
        meta: PathDistribution, extras: Set[str]
    ) -> List[Requirement]:
        result: List[Requirement] = []
        requires = meta.requires or []
        for req_str in requires:
            req = Requirement(req_str)
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
            # continue only if this extra should be included
            if not (extra is None or extra in extras):
                continue
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
        backend = os.pathsep.join(str(i) for i in self._backend_paths).strip()
        if backend:
            env["PYTHONPATH"] = backend
        return env

    def teardown(self) -> None:
        self.ref_count.decrement()
        if self.ref_count.value == 0 and self._backend_executor is not None and self._teardown_done is False:
            self._teardown_done = True
            try:
                if self.backend_executor.is_alive:
                    self._send("_exit")  # try first on amicable shutdown
            except SystemExit:  # if already has been interrupted ignore
                pass
            finally:
                self._backend_executor.close()

    @contextmanager
    def _send_msg(self, cmd: str, result_file: Path, msg: str) -> Iterator[ToxCmdStatus]:  # type: ignore[override]
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
        if outcome is not None:  # pragma: no branch
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

    def _send(self, cmd: str, **kwargs: Any) -> Tuple[Any, str, str]:
        try:
            if cmd == "prepare_metadata_for_build_wheel":
                # given we'll build a wheel we might skip the prepare step
                for pkg_type, pkg_name in self._run_env_to_info.values():
                    if pkg_type is PackageType.wheel and pkg_name == self.conf.name:
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
