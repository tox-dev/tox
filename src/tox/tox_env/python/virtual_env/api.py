"""
Declare the abstract base class for tox environments that handle the Python language via the virtualenv project.
"""
import sys
from abc import ABC
from pathlib import Path
from typing import Dict, List, Optional, Sequence, cast

from virtualenv import __version__ as virtualenv_version
from virtualenv import session_via_cli
from virtualenv.create.creator import Creator
from virtualenv.run.session import Session

from tox.config.cli.parser import DEFAULT_VERBOSITY, Parsed
from tox.config.loader.str_convert import StrConvert
from tox.config.main import Config
from tox.config.sets import CoreConfigSet, EnvConfigSet
from tox.config.types import Command
from tox.execute.api import Execute, Outcome, StdinSource
from tox.execute.local_sub_process import LocalSubProcessExecutor
from tox.journal import EnvJournal
from tox.report import ToxHandler
from tox.tox_env.errors import Recreate

from ..api import Python, PythonDeps, PythonInfo


class VirtualEnv(Python, ABC):
    """A python executor that uses the virtualenv project with pip"""

    def __init__(
        self, conf: EnvConfigSet, core: CoreConfigSet, options: Parsed, journal: EnvJournal, log_handler: ToxHandler
    ) -> None:
        self._virtualenv_session: Optional[Session] = None
        super().__init__(conf, core, options, journal, log_handler)

    def register_config(self) -> None:
        super().register_config()
        self.conf.add_config(
            keys=["system_site_packages", "sitepackages"],
            of_type=bool,
            default=lambda conf, name: StrConvert().to_bool(
                self.environment_variables.get("VIRTUALENV_SYSTEM_SITE_PACKAGES", "False")
            ),
            desc="create virtual environments that also have access to globally installed packages.",
        )
        self.conf.add_config(
            keys=["always_copy", "alwayscopy"],
            of_type=bool,
            default=lambda conf, name: StrConvert().to_bool(
                self.environment_variables.get(
                    "VIRTUALENV_COPIES", self.environment_variables.get("VIRTUALENV_ALWAYS_COPY", "False")
                )
            ),
            desc="force virtualenv to always copy rather than symlink",
        )
        self.conf.add_config(
            keys=["download"],
            of_type=bool,
            default=lambda conf, name: StrConvert().to_bool(
                self.environment_variables.get("VIRTUALENV_DOWNLOAD", "False")
            ),
            desc="true if you want virtualenv to upgrade pip/wheel/setuptools to the latest version",
        )
        self.conf.add_config(
            keys=["pip_pre"],
            of_type=bool,
            default=False,
            desc="install the latest available pre-release (alpha/beta/rc) of dependencies without a specified version",
        )
        self.conf.add_config(
            keys=["install_command"],
            of_type=Command,
            default=self.default_install_command,
            post_process=self.post_process_install_command,
            desc="install the latest available pre-release (alpha/beta/rc) of dependencies without a specified version",
        )
        self.conf.add_config(
            keys=["list_dependencies_command"],
            of_type=Command,
            default=Command(["python", "-m", "pip", "freeze", "--all"]),
            desc="install the latest available pre-release (alpha/beta/rc) of dependencies without a specified version",
        )

    def post_process_install_command(self, cmd: Command) -> Command:
        install_command = cmd.args
        pip_pre: bool = self.conf["pip_pre"]
        try:
            opts_at = install_command.index("{opts}")
        except ValueError:
            if pip_pre:
                install_command.append("--pre")
        else:
            if pip_pre:
                install_command[opts_at] = "--pre"
            else:
                install_command.pop(opts_at)
        return cmd

    def default_install_command(self, conf: Config, env_name: Optional[str]) -> Command:  # noqa
        isolated_flag = "-E" if self.base_python.version_info.major == 2 else "-I"
        cmd = Command(["python", isolated_flag, "-m", "pip", "install", "{opts}", "{packages}"])
        return self.post_process_install_command(cmd)

    def setup(self) -> None:
        with self._cache.compare({"version": virtualenv_version}, VirtualEnv.__name__) as (eq, old):
            if eq is False and old is not None:  # if changed create
                raise Recreate
        super().setup()

    def default_pass_env(self) -> List[str]:
        env = super().default_pass_env()
        env.append("PIP_*")  # we use pip as installer
        env.append("VIRTUALENV_*")  # we use virtualenv as isolation creator
        return env

    def default_set_env(self) -> Dict[str, str]:
        env = super().default_set_env()
        env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
        return env

    def build_executor(self) -> Execute:
        return LocalSubProcessExecutor(self.options.is_colored)

    @property
    def session(self) -> Session:
        if self._virtualenv_session is None:
            env_dir = [str(cast(Path, self.conf["env_dir"]))]
            env = self.virtualenv_env_vars()
            self._virtualenv_session = session_via_cli(env_dir, options=None, setup_logging=False, env=env)
        return self._virtualenv_session

    def virtualenv_env_vars(self) -> Dict[str, str]:
        env = self.environment_variables.copy()
        base_python: List[str] = self.conf["base_python"]
        if "VIRTUALENV_CLEAR" not in env:
            env["VIRTUALENV_CLEAR"] = "True"
        if "VIRTUALENV_NO_PERIODIC_UPDATE" not in env:
            env["VIRTUALENV_NO_PERIODIC_UPDATE"] = "True"
        site = getattr(self.options, "site_packages", False) or self.conf["system_site_packages"]
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

    def python_env_paths(self) -> List[Path]:
        """Paths to add to the executable"""
        # we use the original executable as shims may be somewhere else
        return list(dict.fromkeys((self.creator.bin_dir, self.creator.script_dir)))

    def env_site_package_dir(self) -> Path:
        return cast(Path, self.creator.purelib)

    def env_python(self) -> Path:
        return cast(Path, self.creator.exe)

    def env_bin_dir(self) -> Path:
        return cast(Path, self.creator.script_dir)

    def install_python_packages(
        self,
        packages: PythonDeps,
        of_type: str,
        no_deps: bool = False,
        develop: bool = False,
        force_reinstall: bool = False,
    ) -> None:
        if not packages:
            return

        args: List[str] = []
        if no_deps:
            args.append("--no-deps")
        if force_reinstall:
            args.append("--force-reinstall")
        if develop is True:
            args.extend(("--no-build-isolation", "-e"))
        args.extend(str(i) for i in packages)
        install_command = self.build_install_cmd(args)

        result = self.perform_install(install_command, f"install_{of_type}")
        result.assert_success()

    def build_install_cmd(self, args: Sequence[str]) -> List[str]:
        cmd: Command = self.conf["install_command"]
        install_command = cmd.args
        try:
            opts_at = install_command.index("{packages}")
        except ValueError:
            opts_at = len(install_command)
        result = install_command[:opts_at]
        result.extend(args)
        result.extend(install_command[opts_at + 1 :])
        return result

    def perform_install(self, install_command: Sequence[str], run_id: str) -> Outcome:
        return self.execute(
            cmd=install_command,
            stdin=StdinSource.OFF,
            cwd=self.core["tox_root"],
            run_id=run_id,
            show=self.options.verbosity > DEFAULT_VERBOSITY,
        )

    def get_installed_packages(self) -> List[str]:
        cmd: Command = self.conf["list_dependencies_command"]
        result = self.execute(
            cmd=cmd.args,
            stdin=StdinSource.OFF,
            run_id="freeze",
            show=self.options.verbosity > DEFAULT_VERBOSITY,
        )
        result.assert_success()
        return result.out.splitlines()

    @property
    def runs_on_platform(self) -> str:
        return sys.platform
