"""
Declare the abstract base class for tox environments that handle the Python language via the virtualenv project.
"""
from abc import ABC
from pathlib import Path
from typing import Dict, List, Optional, Sequence, cast

from virtualenv import session_via_cli
from virtualenv.create.creator import Creator
from virtualenv.run.session import Session

from tox.config.cli.parser import DEFAULT_VERBOSITY, Parsed
from tox.config.sets import CoreConfigSet, EnvConfigSet
from tox.execute.api import Execute, Outcome, StdinSource
from tox.execute.local_sub_process import LocalSubProcessExecutor
from tox.journal import EnvJournal
from tox.report import ToxHandler

from ..api import Python, PythonDeps, PythonInfo


class VirtualEnv(Python, ABC):
    """A python executor that uses the virtualenv project with pip"""

    def __init__(
        self, conf: EnvConfigSet, core: CoreConfigSet, options: Parsed, journal: EnvJournal, log_handler: ToxHandler
    ) -> None:
        self._virtualenv_session: Optional[Session] = None  # type: ignore[no-any-unimported]
        super().__init__(conf, core, options, journal, log_handler)

    def default_pass_env(self) -> List[str]:
        env = super().default_pass_env()
        env.append("PIP_*")  # we use pip as installer
        env.append("VIRTUALENV_*")  # we use virtualenv as isolation creator
        return env

    def default_set_env(self) -> Dict[str, str]:
        env = super().default_set_env()
        env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
        env["VIRTUALENV_NO_PERIODIC_UPDATE"] = "1"
        return env

    def build_executor(self) -> Execute:
        return LocalSubProcessExecutor(self.options.is_colored)

    @property
    def session(self) -> Session:  # type: ignore[no-any-unimported]
        if self._virtualenv_session is None:
            args = [
                "--clear",
                "--no-periodic-update",
                str(cast(Path, self.conf["env_dir"])),
            ]
            base_python: List[str] = self.conf["base_python"]
            for base in base_python:
                args.extend(["-p", base])
            self._virtualenv_session = session_via_cli(args, setup_logging=False)
        return self._virtualenv_session

    @property
    def creator(self) -> Creator:  # type: ignore[no-any-unimported]
        return self.session.creator

    def create_python_env(self) -> None:
        self.session.run()

    def _get_python(self, base_python: List[str]) -> Optional[PythonInfo]:
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

    def paths(self) -> List[Path]:
        """Paths to add to the executable"""
        # we use the original executable as shims may be somewhere else
        return list({self.creator.bin_dir, self.creator.script_dir})

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
        install_command = self.base_install_cmd
        if no_deps:
            install_command.append("--no-deps")
        if force_reinstall:
            install_command.append("--force-reinstall")
        if develop is True:
            install_command.extend(("--no-build-isolation", "-e"))
        install_command.extend(str(i) for i in packages)
        result = self.perform_install(install_command, f"install_{of_type}")
        result.assert_success()

    @property
    def base_install_cmd(self) -> List[str]:
        return [str(self.creator.exe), "-I", "-m", "pip", "install"]

    def perform_install(self, install_command: Sequence[str], run_id: str) -> Outcome:
        return self.execute(
            cmd=install_command,
            stdin=StdinSource.OFF,
            cwd=self.core["tox_root"],
            run_id=run_id,
            show=self.options.verbosity > DEFAULT_VERBOSITY,
        )

    def get_installed_packages(self) -> List[str]:
        list_command = [self.creator.exe, "-I", "-m", "pip", "freeze", "--all"]
        result = self.execute(
            cmd=list_command,
            stdin=StdinSource.OFF,
            run_id="freeze",
            show=self.options.verbosity > DEFAULT_VERBOSITY,
        )
        result.assert_success()
        return result.out.splitlines()
