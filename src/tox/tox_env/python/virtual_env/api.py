import shutil
import sys
from abc import ABC
from pathlib import Path
from typing import List, Sequence, Union, cast

from appdirs import user_cache_dir
from packaging.requirements import Requirement

from tox.config.sets import ConfigSet
from tox.execute.api import Outcome
from tox.execute.local_sub_process import LocalSubProcessExecutor
from tox.interpreters.discovery import PythonInfo

from ..api import Python

CACHE_DIR = Path(user_cache_dir(appname="tox", appauthor="tox-dev")) / "virtualenv" / "pip"


def copy_overwrite(src: Path, dest: Path):
    if dest.exists():
        shutil.rmtree(dest)
    if src.is_dir():
        if not dest.is_dir():
            dest.mkdir(parents=True)
        for file_name in src.iterdir():
            copy_overwrite(file_name, dest / file_name.name)
    else:
        shutil.copyfile(str(src), str(dest))


class VirtualEnv(Python, ABC):
    def __init__(self, conf: ConfigSet, core: ConfigSet, options):
        super().__init__(conf, core, options, LocalSubProcessExecutor())

    def create_python_env(self, python: PythonInfo):
        core_cmd = self.core_cmd(python)
        env_dir = cast(Path, self.conf["env_dir"])
        # installing pip is slow - speed up by cache-ing pip
        cmd = core_cmd + ("--no-pip", "--clear", env_dir)
        result = self.execute(cmd=cmd, allow_stdin=False)
        result.assert_success(self.logger)
        self._bootstrap_pip(core_cmd, env_dir)

    @staticmethod
    def core_cmd(python):
        core_cmd = (
            sys.executable,
            "-m",
            "virtualenv",
            "--no-setuptools",
            "--no-wheel",
            "--no-download",
            "--python",
            python.executable,
        )
        return core_cmd

    def _bootstrap_pip(self, core_cmd, env_dir):
        self._get_cached_pip(core_cmd)
        self._install_pip_from_cache(env_dir)

    def _get_cached_pip(self, core_cmd):
        if not CACHE_DIR.exists():
            CACHE_DIR.mkdir(parents=True)
            cmd = core_cmd + ("--clear", CACHE_DIR)
            result = self.execute(cmd=cmd, allow_stdin=False)
            result.assert_success(self.logger)

    def _install_pip_from_cache(self, env_dir):
        package = self.get_site_packages(CACHE_DIR)
        target_folder = self.get_site_packages(env_dir)
        copy_overwrite(package, target_folder)
        target_folder = self.get_bin(env_dir)
        for binary in [b for b in self.get_bin(CACHE_DIR).iterdir() if "pip" in b.name]:
            target_file = target_folder / binary.name
            shutil.copyfile(str(binary), target_file)
            content = binary.read_text()
            content.replace(str(CACHE_DIR), str(env_dir))
            target_file.write_text(content)

    @staticmethod
    def get_bin(folder: Path) -> Path:
        return next(p for p in folder.iterdir() if p.name in ("bin", "Script"))

    @staticmethod
    def get_site_packages(folder: Path) -> Path:
        lib = next(next(i for i in folder.iterdir() if i.name in ("lib", "Lib")).iterdir())
        return lib / "site-packages"

    def paths(self, python: PythonInfo) -> List[Path]:
        # we use the original executable as shims may be somewhere else
        host_postfix = Path(python.original_executable).relative_to(python.prefix).parent
        return [self.conf["env_dir"] / host_postfix]

    def python_cache(self, python: PythonInfo):
        return {"version_info": list(python.version_info), "executable": python.executable}

    def install_python_packages(
        self,
        packages: List[Union[Requirement, Path]],
        no_deps: bool = False,
        develop=False,
        force_reinstall=False,
    ) -> None:
        if packages:
            install_command = self.install_command(develop, force_reinstall, no_deps, packages)
            result = self.perform_install(install_command)
            result.assert_success(self.logger)

    def perform_install(self, install_command: Sequence[str]) -> Outcome:
        return self.execute(cmd=install_command, allow_stdin=False)

    # noinspection PyMethodMayBeStatic
    def install_command(self, develop, force_reinstall, no_deps, packages):
        install_command = ["python", "-m", "pip", "--disable-pip-version-check", "install"]
        if develop is True:
            install_command.append("-e")
        if no_deps:
            install_command.append("--no-deps")
        if force_reinstall:
            install_command.append("--force-reinstall")
        install_command.extend(str(i) for i in packages)
        return install_command
