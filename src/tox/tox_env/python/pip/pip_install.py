import logging
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

from packaging.requirements import Requirement

from tox.config.cli.parser import DEFAULT_VERBOSITY
from tox.config.main import Config
from tox.config.types import Command
from tox.execute.request import StdinSource
from tox.report import HandledError
from tox.tox_env.errors import Recreate
from tox.tox_env.installer import Installer
from tox.tox_env.package import PathPackage
from tox.tox_env.python.api import Python
from tox.tox_env.python.package import DevLegacyPackage, SdistPackage, WheelPackage
from tox.tox_env.python.pip.req_file import PythonDeps


class Pip(Installer[Python]):
    """Pip is a python installer that can install packages as defined by PEP-508 and PEP-517"""

    def __init__(self, tox_env: Python, with_list_deps: bool = True) -> None:
        self._with_list_deps = with_list_deps
        super().__init__(tox_env)

    def _register_config(self) -> None:
        self._env.conf.add_config(
            keys=["pip_pre"],
            of_type=bool,
            default=False,
            desc="install the latest available pre-release (alpha/beta/rc) of dependencies without a specified version",
        )
        self._env.conf.add_config(
            keys=["install_command"],
            of_type=Command,
            default=self.default_install_command,
            post_process=self.post_process_install_command,
            desc="command used to install packages",
        )
        if self._with_list_deps:  # pragma: no branch
            self._env.conf.add_config(
                keys=["list_dependencies_command"],
                of_type=Command,
                default=Command(["python", "-m", "pip", "freeze", "--all"]),
                desc="command used to list isntalled packages",
            )

    def default_install_command(self, conf: Config, env_name: Optional[str]) -> Command:  # noqa: U100
        isolated_flag = "-E" if self._env.base_python.version_info.major == 2 else "-I"
        cmd = Command(["python", isolated_flag, "-m", "pip", "install", "{opts}", "{packages}"])
        return self.post_process_install_command(cmd)

    def post_process_install_command(self, cmd: Command) -> Command:
        install_command = cmd.args
        pip_pre: bool = self._env.conf["pip_pre"]
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

    def installed(self) -> List[str]:
        cmd: Command = self._env.conf["list_dependencies_command"]
        result = self._env.execute(
            cmd=cmd.args,
            stdin=StdinSource.OFF,
            run_id="freeze",
            show=self._env.options.verbosity > DEFAULT_VERBOSITY,
        )
        result.assert_success()
        return result.out.splitlines()

    def install(self, arguments: Any, section: str, of_type: str) -> None:
        if isinstance(arguments, PythonDeps):
            self._install_requirement_file(arguments, section, of_type)
        elif isinstance(arguments, Sequence):
            self._install_list_of_deps(arguments, section, of_type)
        else:
            logging.warning(f"pip cannot install {arguments!r}")
            raise SystemExit(1)

    def _install_requirement_file(self, arguments: PythonDeps, section: str, of_type: str) -> None:
        try:
            new_options, new_reqs = arguments.unroll()
        except ValueError as exception:
            raise HandledError(f"{exception} for tox env py within deps")
        new_requirements: List[str] = []
        new_constraints: List[str] = []
        for req in new_reqs:
            (new_constraints if req.startswith("-c ") else new_requirements).append(req)
        new = {"options": new_options, "requirements": new_requirements, "constraints": new_constraints}
        # if option or constraint change in any way recreate, if the requirements change only if some are removed
        with self._env.cache.compare(new, section, of_type) as (eq, old):
            if not eq:  # pragma: no branch
                if old is not None:
                    self._recreate_if_diff("install flag(s)", new_options, old["options"], lambda i: i)
                    self._recreate_if_diff("constraint(s)", new_constraints, old["constraints"], lambda i: i[3:])
                    missing_requirement = set(old["requirements"]) - set(new_requirements)
                    if missing_requirement:
                        raise Recreate(f"requirements removed: {' '.join(missing_requirement)}")
                args = arguments.as_root_args
                if args:  # pragma: no branch
                    self._execute_installer(args, of_type)

    @staticmethod
    def _recreate_if_diff(of_type: str, new_opts: List[str], old_opts: List[str], fmt: Callable[[str], str]) -> None:
        if old_opts == new_opts:
            return
        removed_opts = set(old_opts) - set(new_opts)
        removed = f" removed {', '.join(sorted(fmt(i) for i in removed_opts))}" if removed_opts else ""
        added_opts = set(new_opts) - set(old_opts)
        added = f" added {', '.join(sorted(fmt(i) for i in added_opts))}" if added_opts else ""
        raise Recreate(f"changed {of_type}{removed}{added}")

    def _install_list_of_deps(
        self,
        arguments: Sequence[Union[Requirement, WheelPackage, SdistPackage, DevLegacyPackage, PathPackage]],
        section: str,
        of_type: str,
    ) -> None:
        groups: Dict[str, List[str]] = defaultdict(list)
        for arg in arguments:
            if isinstance(arg, Requirement):
                groups["req"].append(str(arg))
            elif isinstance(arg, (WheelPackage, SdistPackage)):
                groups["req"].extend(str(i) for i in arg.deps)
                groups["pkg"].append(str(arg.path))
            elif isinstance(arg, DevLegacyPackage):
                groups["req"].extend(str(i) for i in arg.deps)
                groups["dev_pkg"].append(str(arg.path))
            elif isinstance(arg, PathPackage):
                groups["path_pkg"].append(str(arg.path))
            else:
                logging.warning(f"pip cannot install {arg!r}")
                raise SystemExit(1)
        req_of_type = f"{of_type}_deps" if groups["pkg"] or groups["dev_pkg"] else of_type
        for value in groups.values():
            value.sort()
        with self._env.cache.compare(groups["req"], section, req_of_type) as (eq, old):
            if not eq:  # pragma: no branch
                miss = sorted(set(old or []) - set(groups["req"]))
                if miss:  # no way yet to know what to uninstall here (transitive dependencies?)
                    raise Recreate(f"dependencies removed: {', '.join(str(i) for i in miss)}")  # pragma: no branch
                new_deps = sorted(set(groups["req"]) - set(old or []))
                if new_deps:  # pragma: no branch
                    self._execute_installer(new_deps, req_of_type)
        install_args = ["--force-reinstall", "--no-deps"]
        if groups["pkg"]:
            self._execute_installer(install_args + groups["pkg"], of_type)
        if groups["dev_pkg"]:
            for entry in groups["dev_pkg"]:
                install_args.extend(("-e", str(entry)))
            self._execute_installer(install_args, of_type)
        if groups["path_pkg"]:
            self._execute_installer(groups["path_pkg"], of_type)

    def _execute_installer(self, deps: Sequence[Any], of_type: str) -> None:
        cmd = self.build_install_cmd(deps)
        outcome = self._env.execute(cmd, stdin=StdinSource.OFF, run_id=f"install_{of_type}")
        outcome.assert_success()

    def build_install_cmd(self, args: Sequence[str]) -> List[str]:
        cmd: Command = self._env.conf["install_command"]
        install_command = cmd.args
        try:
            opts_at = install_command.index("{packages}")
        except ValueError:
            opts_at = len(install_command)
        result = install_command[:opts_at] + list(args) + install_command[opts_at + 1 :]
        return result


__all__ = ("Pip",)
