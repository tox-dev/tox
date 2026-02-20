"""Declare the abstract base class for tox environments that handle the Python language via the virtualenv project."""

from __future__ import annotations

import os
import sys
from abc import ABC
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from virtualenv import __version__ as virtualenv_version
from virtualenv import app_data, session_via_cli
from virtualenv.discovery import cached_py_info
from virtualenv.discovery.py_spec import PythonSpec

from tox.config.loader.str_convert import StrConvert
from tox.execute.local_sub_process import LocalSubProcessExecutor
from tox.tox_env.errors import Skip
from tox.tox_env.python.api import Python, PythonInfo, VersionInfo
from tox.tox_env.python.pip.pip_install import Pip
from tox.tox_env.python.virtual_env.subprocess_adapter import SubprocessCreator, SubprocessSession

if TYPE_CHECKING:
    from virtualenv.create.creator import Creator
    from virtualenv.create.describe import Describe
    from virtualenv.discovery.py_info import PythonInfo as VirtualenvPythonInfo
    from virtualenv.run.session import Session

    from tox.execute.api import Execute
    from tox.tox_env.api import ToxEnvCreateArgs


class VirtualEnv(Python, ABC):
    """A python executor that uses the virtualenv project with pip."""

    def __init__(self, create_args: ToxEnvCreateArgs) -> None:
        self._virtualenv_session: Session | SubprocessSession | None = None
        self._executor: Execute | None = None
        self._installer: Pip | None = None
        super().__init__(create_args)

    def register_config(self) -> None:
        super().register_config()
        self.conf.add_config(
            keys=["system_site_packages", "sitepackages"],
            of_type=bool,
            default=lambda conf, name: StrConvert().to_bool(  # noqa: ARG005
                self.environment_variables.get("VIRTUALENV_SYSTEM_SITE_PACKAGES", "False"),
            ),
            desc="create virtual environments that also have access to globally installed packages.",
        )
        self.conf.add_config(
            keys=["always_copy", "alwayscopy"],
            of_type=bool,
            default=lambda conf, name: StrConvert().to_bool(  # noqa: ARG005
                self.environment_variables.get(
                    "VIRTUALENV_COPIES",
                    self.environment_variables.get("VIRTUALENV_ALWAYS_COPY", "False"),
                ),
            ),
            desc="force virtualenv to always copy rather than symlink",
        )
        self.conf.add_config(
            keys=["download"],
            of_type=bool,
            default=lambda conf, name: StrConvert().to_bool(  # noqa: ARG005
                self.environment_variables.get("VIRTUALENV_DOWNLOAD", "False"),
            ),
            desc="true if you want virtualenv to upgrade pip/wheel/setuptools to the latest version",
        )
        self.conf.add_config(
            keys=["virtualenv_spec"],
            of_type=str,
            default="",
            desc="PEP 440 version spec for virtualenv (e.g. virtualenv<20.22.0). When set, tox bootstraps this "
            "version in an isolated environment and runs it via subprocess, enabling Python versions "
            "incompatible with the installed virtualenv.",
        )

    @property
    def executor(self) -> Execute:
        if self._executor is None:
            self._executor = LocalSubProcessExecutor(self.options.is_colored)
        return self._executor

    @property
    def installer(self) -> Pip:
        if self._installer is None:
            self._installer = Pip(self)
        return self._installer

    def python_cache(self) -> dict[str, Any]:
        base = super().python_cache()
        base["executable"] = str(self.base_python.extra["executable"])
        if spec := self.conf["virtualenv_spec"]:
            base["virtualenv_spec"] = spec
        else:
            base["virtualenv version"] = virtualenv_version
        return base

    def _get_env_journal_python(self) -> dict[str, Any]:
        base = super()._get_env_journal_python()
        base["executable"] = str(self.base_python.extra["executable"])
        return base

    def _default_pass_env(self) -> list[str]:
        env = super()._default_pass_env()
        env.append("PIP_*")  # we use pip as installer
        env.append("VIRTUALENV_*")  # we use virtualenv as isolation creator
        return env

    def _default_set_env(self) -> dict[str, str]:
        env = super()._default_set_env()
        env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
        return env

    @property
    def session(self) -> Session | SubprocessSession:
        if self._virtualenv_session is None:
            env = self.virtualenv_env_vars()
            if spec := self.conf["virtualenv_spec"]:
                self._virtualenv_session = self._create_subprocess_session(spec, env)
            else:
                self._virtualenv_session = self._create_imported_session(env)
        return self._virtualenv_session

    def _create_subprocess_session(self, spec: str, env: dict[str, str]) -> SubprocessSession:
        from .subprocess_adapter import ensure_bootstrap, probe_python  # noqa: PLC0415

        bootstrap_python = ensure_bootstrap(cast("Path", self.core["work_dir"]), spec)
        base_pythons: list[str] = self.conf["base_python"]
        interpreter = next((info for bp in base_pythons if (info := probe_python(bp)) is not None), None)
        return SubprocessSession(self.env_dir, bootstrap_python, env, interpreter)

    def _create_imported_session(self, env: dict[str, str]) -> Session:
        env_dir = [str(self.env_dir)]
        try:
            with redirect_stderr(StringIO()):
                return session_via_cli(env_dir, options=None, setup_logging=False, env=env)
        except SystemExit as exc:
            msg = f"virtualenv session creation failed for {env_dir[0]}"
            raise RuntimeError(msg) from exc

    def virtualenv_env_vars(self) -> dict[str, str]:
        env = self.environment_variables.copy()
        base_python: list[str] = self.conf["base_python"]
        if "VIRTUALENV_NO_PERIODIC_UPDATE" not in env:
            env["VIRTUALENV_NO_PERIODIC_UPDATE"] = "True"
        env["VIRTUALENV_CLEAR"] = "False"
        env["VIRTUALENV_SYSTEM_SITE_PACKAGES"] = str(self.conf["system_site_packages"])
        env["VIRTUALENV_COPIES"] = str(self.conf["always_copy"])
        env["VIRTUALENV_DOWNLOAD"] = str(self.conf["download"])
        env["VIRTUALENV_PYTHON"] = "\n".join(base_python)
        if hasattr(self.options, "discover"):
            env["VIRTUALENV_TRY_FIRST_WITH"] = os.pathsep.join(self.options.discover)
        return env

    @property
    def creator(self) -> Creator | SubprocessCreator:
        return self.session.creator

    def create_python_env(self) -> None:
        self.session.run()

    def _get_python(self, base_python: list[str]) -> PythonInfo | None:  # noqa: ARG002
        # the base pythons are injected into the virtualenv_env_vars, so we don't need to use it here
        try:
            interpreter = self.creator.interpreter
        except (FileNotFoundError, RuntimeError):  # Unable to find the interpreter
            return None
        vi = interpreter.version_info
        return PythonInfo(
            implementation=interpreter.implementation,
            version_info=VersionInfo(vi.major, vi.minor, vi.micro, vi.releaselevel, vi.serial),
            version=interpreter.version,
            is_64=(interpreter.architecture == 64),  # noqa: PLR2004
            platform=interpreter.platform,
            extra={"executable": Path(interpreter.system_executable).resolve()},
            free_threaded=interpreter.free_threaded,
        )

    def prepend_env_var_path(self) -> list[Path]:
        """Paths to add to the executable."""
        creator = self._creator_with_skip()
        if isinstance(creator, SubprocessCreator):
            return list(dict.fromkeys((creator.bin_dir, creator.script_dir)))
        described = cast("Describe", creator)
        return list(dict.fromkeys((described.bin_dir, described.script_dir)))

    def env_site_package_dir(self) -> Path:
        return self._describe_path("purelib")

    def env_site_package_dir_plat(self) -> Path:
        return self._describe_path("platlib")

    def env_python(self) -> Path:
        return self._describe_path("exe")

    def env_bin_dir(self) -> Path:
        return self._describe_path("script_dir")

    def _describe_path(self, attr: str) -> Path:
        creator = self._creator_with_skip()
        if isinstance(creator, SubprocessCreator):
            return getattr(creator, attr)
        return cast("Path", getattr(cast("Describe", creator), attr))

    def _creator_with_skip(self) -> Creator | SubprocessCreator:
        try:
            return self.creator
        except RuntimeError as exc:
            raise Skip(str(exc)) from exc

    @property
    def runs_on_platform(self) -> str:
        return sys.platform

    @property
    def environment_variables(self) -> dict[str, str]:
        environment_variables = super().environment_variables
        environment_variables["VIRTUAL_ENV"] = str(self.conf["env_dir"])
        environment_variables["PIP_USER"] = "0"
        return environment_variables

    @classmethod
    def python_spec_for_path(cls, path: Path) -> PythonSpec:
        """Get the spec for an absolute path to a Python executable.

        :param path: the path investigated

        :returns: the found spec

        """
        info = cls.get_virtualenv_py_info(path)
        return PythonSpec.from_string_spec(
            f"{info.implementation}{info.version_info.major}{info.version_info.minor}-{info.architecture}"
        )

    @staticmethod
    def get_virtualenv_py_info(path: Path) -> VirtualenvPythonInfo:
        """Get the version info for an absolute path to a Python executable.

        :param path: the path investigated

        :returns: the found information (cached)

        """
        return cached_py_info.from_exe(
            cached_py_info.PythonInfo,
            app_data.make_app_data(None, read_only=False, env=os.environ),
            str(path),
        )
