"""
This package handles provisioning an appropriate tox version per requirements.
"""
import logging
import sys
from argparse import ArgumentParser
from typing import List, Tuple, Union, cast

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

from tox.config.loader.memory import MemoryLoader
from tox.config.main import Config
from tox.config.sets import ConfigSet
from tox.execute.api import StdinSource
from tox.plugin.impl import impl
from tox.session.state import State
from tox.tox_env.python.req_file import RequirementsFile
from tox.tox_env.python.runner import PythonRun
from tox.tox_env.python.virtual_env.package.api import PackageType
from tox.version import __version__ as current_version

if sys.version_info >= (3, 8):  # pragma: no cover (py38+)
    from importlib.metadata import PackageNotFoundError, distribution
else:  # pragma: no cover (py38+)
    from importlib_metadata import PackageNotFoundError, distribution  # noqa


@impl
def tox_add_option(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--no-recreate-provision",
        dest="recreate",
        help="if recreate is set do not recreate provision tox environment",
        action="store_true",
    )


@impl
def tox_add_core_config(core: ConfigSet) -> None:
    core.add_config(
        keys=["min_version", "minversion"],
        of_type=Version,
        # do not include local version specifier (because it's not allowed in version spec per PEP-440)
        default=Version(current_version.split("+")[0]),
        desc="Define the minimal tox version required to run",
    )
    core.add_config(
        keys="provision_tox_env",
        of_type=str,
        default=".tox",
        desc="Name of the virtual environment used to provision a tox.",
    )

    def add_tox_requires_min_version(requires: List[Requirement], conf: Config) -> List[Requirement]:
        min_version: Version = conf.core["min_version"]
        requires.append(Requirement(f"tox >= {min_version.public}"))
        return requires

    core.add_config(
        keys="requires",
        of_type=List[Requirement],
        default=[],
        desc="Name of the virtual environment used to provision a tox.",
        post_process=add_tox_requires_min_version,
    )


def provision(state: State) -> Union[int, bool]:
    requires: List[Requirement] = state.conf.core["requires"]
    missing: List[Tuple[Requirement, str]] = []
    for package in requires:
        package_name = canonicalize_name(package.name)
        try:
            dist = distribution(package_name)  # type: ignore[no-untyped-call]
            if not package.specifier.contains(dist.version, prereleases=True):
                missing.append((package, dist.version))
        except PackageNotFoundError:
            missing.append((package, "N/A"))
    if not missing:
        return False
    deps = ", ".join(f"{p} ({ver})" for p, ver in missing)
    logging.warning(
        "will run in automatically provisioned tox, host %s is missing [requires (has)]: %s", sys.executable, deps
    )
    return run_provision(requires, state)


def run_provision(deps: List[Requirement], state: State) -> int:  # noqa
    """"""
    loader = MemoryLoader(  # these configuration values are loaded from in-memory always (no file conf)
        base=[],  # disable inheritance for provision environments
        package=PackageType.skip,  # no packaging for this please
        # use our own dependency specification
        deps=RequirementsFile("\n".join(str(d) for d in deps), root=state.conf.core["tox_root"]),
        pass_env=["*"],  # do not filter environment variables, will be handled by provisioned tox
    )
    provision_tox_env: str = state.conf.core["provision_tox_env"]
    state.conf.get_env(provision_tox_env, loaders=[loader])
    tox_env = cast(PythonRun, state.tox_env(provision_tox_env))
    env_python = tox_env.env_python()
    logging.info("will run in a automatically provisioned python environment under %s", env_python)
    recreate = state.options.no_recreate_provision is False if state.options.recreate else False
    tox_env.ensure_setup(recreate=recreate)
    args: List[str] = [str(env_python), "-m", "tox"]
    args.extend(state.args)
    outcome = tox_env.execute(cmd=args, stdin=StdinSource.user_only(), show=True, run_id="provision")
    return cast(int, outcome.exit_code)
