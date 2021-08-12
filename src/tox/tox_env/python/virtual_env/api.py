"""
Declare the abstract base class for tox environments that handle the Python language via the virtualenv project.
"""
import sys
from abc import ABC
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

from virtualenv import __version__ as virtualenv_version
from virtualenv import session_via_cli
from virtualenv.create.creator import Creator
from virtualenv.run.session import Session

from tox.config.cli.parser import Parsed
from tox.config.loader.str_convert import StrConvert
from tox.config.sets import CoreConfigSet, EnvConfigSet
from tox.execute.api import Execute
from tox.execute.local_sub_process import LocalSubProcessExecutor
from tox.journal import EnvJournal
from tox.report import ToxHandler
from tox.tox_env.python.pip.pip_install import Pip

from ..api import Python, PythonInfo


class VirtualEnv(Python, ABC):
    """A python executor that uses the virtualenv project with pip"""

    def __init__(
        self, conf: EnvConfigSet, core: CoreConfigSet, options: Parsed, journal: EnvJournal, log_handler: ToxHandler
    ) -> None:
        self._virtualenv_session: Optional[Session] = None
        self._executor: Optional[Execute] = None
        self._installer: Optional[Pip] = None
        super().__init__(conf, core, options, journal, log_handler)

    def register_config(self) -> None:
        super().register_config()
        self.conf.add_config(
            keys=["system_site_packages", "sitepackages"],
            of_type=bool,
            default=lambda conf, name: StrConvert().to_bool(
                self._environment_variables.get("VIRTUALENV_SYSTEM_SITE_PACKAGES", "False")
            ),
            desc="create virtual environments that also have access to globally installed packages.",
        )
        self.conf.add_config(
            keys=["always_copy", "alwayscopy"],
            of_type=bool,
            default=lambda conf, name: StrConvert().to_bool(
                self._environment_variables.get(
                    "VIRTUALENV_COPIES", self._environment_variables.get("VIRTUALENV_ALWAYS_COPY", "False")
                )
            ),
            desc="force virtualenv to always copy rather than symlink",
        )
        self.conf.add_config(
            keys=["download"],
            of_type=bool,
            default=lambda conf, name: StrConvert().to_bool(
                self._environment_variables.get("VIRTUALENV_DOWNLOAD", "False")
            ),
            desc="true if you want virtualenv to upgrade pip/wheel/setuptools to the latest version",
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

    def python_cache(self) -> Dict[str, Any]:
        base = super().python_cache()
        base["virtualenv version"] = virtualenv_version
        return base

    def _default_pass_env(self) -> List[str]:
        env = super()._default_pass_env()
        env.append("PIP_*")  # we use pip as installer
        env.append("VIRTUALENV_*")  # we use virtualenv as isolation creator
        return env

    def _default_set_env(self) -> Dict[str, str]:
        env = super()._default_set_env()
        env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
        return env

    @property
    def session(self) -> Session:
        if self._virtualenv_session is None:
            env_dir = [str(self.env_dir)]
            env = self.virtualenv_env_vars()
            self._virtualenv_session = session_via_cli(env_dir, options=None, setup_logging=False, env=env)
        return self._virtualenv_session

    def virtualenv_env_vars(self) -> Dict[str, str]:
        env = self._environment_variables.copy()
        base_python: List[str] = self.conf["base_python"]
        if "VIRTUALENV_NO_PERIODIC_UPDATE" not in env:
            env["VIRTUALENV_NO_PERIODIC_UPDATE"] = "True"
        site = getattr(self.options, "site_packages", False) or self.conf["system_site_packages"]
        env["VIRTUALENV_CLEAR"] = "False"
        env["VIRTUALENV_SYSTEM_SITE_PACKAGES"] = str(site)
        env["VIRTUALENV_COPIES"] = str(getattr(self.options, "always_copy", False) or self.conf["always_copy"])
        env["VIRTUALENV_DOWNLOAD"] = str(self.conf["download"])
        env["VIRTUALENV_PYTHON"] = "\n".join(base_python)
        return env

    @property
    def creator(self) -> Creator:
        return self.session.creator

    def create_python_env(self) -> None:
        self.session.run()

    def _get_python(self, base_python: List[str]) -> Optional[PythonInfo]:  # noqa: U100
        # the base pythons is injected into the virtualenv_env_vars, so we don't need to use it here
        try:
            interpreter = self.creator.interpreter
        except RuntimeError:  # if can't find
            return None
        return PythonInfo(
            executable=Path(interpreter.system_executable),
            implementation=interpreter.implementation,
            version_info=interpreter.version_info,
            version=interpreter.version,
            is_64=(interpreter.architecture == 64),
            platform=interpreter.platform,
            extra_version_info=None,
        )

    def prepend_env_var_path(self) -> List[Path]:
        """Paths to add to the executable"""
        # we use the original executable as shims may be somewhere else
        return list(dict.fromkeys((self.creator.bin_dir, self.creator.script_dir)))

    def env_site_package_dir(self) -> Path:
        return cast(Path, self.creator.purelib)

    def env_python(self) -> Path:
        return cast(Path, self.creator.exe)

    def env_bin_dir(self) -> Path:
        return cast(Path, self.creator.script_dir)

    @property
    def runs_on_platform(self) -> str:
        return sys.platform
