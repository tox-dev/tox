import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence, Set, Union

from packaging.requirements import Requirement

from tox.config.cli.parser import DEFAULT_VERBOSITY
from tox.config.main import Config
from tox.config.types import Command
from tox.execute.request import StdinSource
from tox.tox_env.errors import Recreate
from tox.tox_env.installer import Installer
from tox.tox_env.package import PathPackage
from tox.tox_env.python.api import Python
from tox.tox_env.python.package import DevLegacyPackage, SdistPackage, WheelPackage
from tox.tox_env.python.pip.req_file import (
    ConstraintFile,
    EditablePathReq,
    Flags,
    PathReq,
    PythonDeps,
    RequirementsFile,
    UrlReq,
)


class Pip(Installer[Python]):
    """Pip is a python installer that can install packages as defined by PEP-508 and PEP-517 """

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
            desc="install the latest available pre-release (alpha/beta/rc) of dependencies without a specified version",
        )
        self._env.conf.add_config(
            keys=["list_dependencies_command"],
            of_type=Command,
            default=Command(["python", "-m", "pip", "freeze", "--all"]),
            desc="install the latest available pre-release (alpha/beta/rc) of dependencies without a specified version",
        )

    def default_install_command(self, conf: Config, env_name: Optional[str]) -> Command:  # noqa
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
        result = arguments.validate_and_expand()
        new_set = arguments.unroll()
        # content we can have here in a nested fashion
        # the the entire universe does not resolve anymore, therefore we only cache the first level
        # root level -> Union[Flags, Requirement, PathReq, EditablePathReq, UrlReq, ConstraintFile, RequirementsFile]
        # if the constraint file changes recreate
        with self._env.cache.compare(new_set, section, of_type) as (eq, old):
            if not eq:  # pick all options and constraint files, do not pick other equal requirements
                new_deps: List[str] = []
                found: Set[int] = set()
                has_dep = False
                for entry, as_cache in zip(result, new_set):
                    entry_as_str = str(entry)
                    found_pos = None
                    for at_pos, value in enumerate(old or []):
                        if (next(iter(value)) if isinstance(value, dict) else value) == entry_as_str:
                            found_pos = at_pos
                            break
                    if found_pos is not None:
                        found.add(found_pos)
                    if isinstance(entry, Flags):
                        if found_pos is None and old is not None:
                            raise Recreate(f"new flag {entry}")
                        new_deps.extend(entry.as_args())
                    elif isinstance(entry, Requirement):
                        if found_pos is None:
                            has_dep = True
                            new_deps.append(str(entry))
                    elif isinstance(entry, (PathReq, EditablePathReq, UrlReq)):
                        if found_pos is None:
                            has_dep = True
                            new_deps.extend(entry.as_args())
                    elif isinstance(entry, ConstraintFile):
                        if found_pos is None and old is not None:
                            raise Recreate(f"new constraint file {entry}")
                        if old is not None and old[found_pos] != as_cache:
                            raise Recreate(f"constraint file {entry.rel_path} changed")
                        new_deps.extend(entry.as_args())
                    elif isinstance(entry, RequirementsFile):
                        if found_pos is None:
                            has_dep = True
                            new_deps.extend(entry.as_args())
                        elif old is not None and old[found_pos] != as_cache:
                            raise Recreate(f"requirements file {entry.rel_path} changed")
                    else:
                        # can only happen when we introduce new content and we don't handle it in any of the branches
                        logging.warning(f"pip cannot install {entry!r}")  # pragma: no cover
                        raise SystemExit(1)  # pragma: no cover
                if len(found) != len(old or []):
                    missing = " ".join(
                        (next(iter(o)) if isinstance(o, dict) else o) for i, o in enumerate(old or []) if i not in found
                    )
                    raise Recreate(f"dependencies removed: {missing}")
                if new_deps:
                    if not has_dep:
                        logging.warning(f"no dependencies for tox env {self._env.name} within {of_type}")
                        raise SystemExit(1)
                    self._execute_installer(new_deps, of_type)

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
            if not eq:
                miss = sorted(set(old or []) - set(groups["req"]))
                if miss:  # no way yet to know what to uninstall here (transitive dependencies?)
                    raise Recreate(f"dependencies removed: {', '.join(str(i) for i in miss)}")  # pragma: no branch
                new_deps = sorted(set(groups["req"]) - set(old or []))
                if new_deps:
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
        result = install_command[:opts_at]
        result.extend(args)
        result.extend(install_command[opts_at + 1 :])
        return result


__all__ = ("Pip",)
