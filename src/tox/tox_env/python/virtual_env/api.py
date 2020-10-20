"""
Declare the abstract base class for tox environments that handle the Python language via the virtualenv project.
"""
from abc import ABC
from pathlib import Path
from typing import List, Optional, Sequence, cast

from virtualenv import session_via_cli
from virtualenv.create.creator import Creator
from virtualenv.discovery.builtin import get_interpreter
from virtualenv.run.session import Session

from tox.config.cli.parser import Parsed
from tox.config.sets import ConfigSet
from tox.execute.api import Execute, Outcome
from tox.execute.local_sub_process import LocalSubProcessExecutor

from ..api import Deps, Python, PythonInfo


class VirtualEnv(Python, ABC):
    def __init__(self, conf: ConfigSet, core: ConfigSet, options: Parsed):
        super().__init__(conf, core, options)
        self._virtualenv_session: Optional[Session] = None

    def executor(self) -> Execute:
        return LocalSubProcessExecutor()

    @property
    def session(self) -> Session:
        if self._virtualenv_session is None:
            args = [
                "--no-periodic-update",
                "-p",
                self.base_python.executable,
                "--clear",
                str(cast(Path, self.conf["env_dir"])),
            ]
            self._virtualenv_session = session_via_cli(args, setup_logging=False)
        return self._virtualenv_session

    @property
    def creator(self) -> Creator:
        return self.session.creator

    def create_python_env(self) -> None:
        self.session.run()

    def _get_python(self, base_python: str) -> PythonInfo:
        info = get_interpreter(base_python)
        return PythonInfo(info.version_info, info.system_executable)

    def paths(self) -> List[Path]:
        """Paths to add to the executable"""
        # we use the original executable as shims may be somewhere else
        return list({self.creator.bin_dir, self.creator.script_dir})

    def env_site_package_dir(self) -> Path:
        return cast(Path, self.creator.purelib)

    def install_python_packages(
        self,
        packages: Deps,
        no_deps: bool = False,
        develop: bool = False,
        force_reinstall: bool = False,
    ) -> None:
        if not packages:
            return
        install_command = [self.creator.exe, "-m", "pip", "--disable-pip-version-check", "install"]
        if develop is True:
            install_command.append("-e")
        if no_deps:
            install_command.append("--no-deps")
        if force_reinstall:
            install_command.append("--force-reinstall")
        install_command.extend(str(i) for i in packages)
        result = self.perform_install(install_command)
        result.assert_success(self.logger)

    def perform_install(self, install_command: Sequence[str]) -> Outcome:
        return self.execute(cmd=install_command, allow_stdin=False)
