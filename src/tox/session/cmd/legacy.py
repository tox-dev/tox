from pathlib import Path

from tox.config.cli.parser import DEFAULT_VERBOSITY, ToxParser
from tox.plugin.impl import impl
from tox.session.cmd.run.common import env_run_create_flags
from tox.session.cmd.run.parallel import OFF_VALUE, parallel_flags, run_parallel
from tox.session.cmd.run.sequential import run_sequential
from tox.session.common import env_list_flag
from tox.session.state import State

from .devenv import devenv
from .list_env import list_env
from .show_config import show_config


@impl
def tox_add_option(parser: ToxParser) -> None:
    our = parser.add_command("legacy", ["le"], "legacy entry-point command", legacy)
    our.add_argument("--help-ini", "--hi", action="store_true", help="show live configuration", dest="show_config")
    our.add_argument(
        "--showconfig",
        action="store_true",
        help="show live configuration (by default all env, with -l only default targets, specific via TOXENV/-e)",
        dest="show_config",
    )
    our.add_argument(
        "-a",
        "--listenvs-all",
        action="store_true",
        help="show list of all defined environments (with description if verbose)",
        dest="list_envs_all",
    )
    our.add_argument(
        "-l",
        "--listenvs",
        action="store_true",
        help="show list of test environments (with description if verbose)",
        dest="list_envs",
    )
    our.add_argument(
        "--devenv",
        help="sets up a development environment at ENVDIR based on the env's tox configuration specified by"
        "`-e` (-e defaults to py)",
        dest="devenv_path",
        metavar="ENVDIR",
        default=None,
        of_type=Path,
    )
    env_list_flag(our)
    env_run_create_flags(our)
    parallel_flags(our, default_parallel=OFF_VALUE)
    our.add_argument(
        "--pre",
        action="store_true",
        help="install pre-releases and development versions of dependencies. This will pass the --pre option to"
        "install_command (pip by default).",
    )
    our.add_argument(
        "-i",
        "--index-url",
        action="append",
        default=[],
        metavar="url",
        help="set indexserver url (if URL is of form name=url set the url for the 'name' indexserver, specifically)",
    )
    our.add_argument(
        "--force-dep",
        action="append",
        metavar="req",
        default=[],
        help="Forces a certain version of one of the dependencies when configuring the virtual environment. REQ "
        "Examples 'pytest<6.1' or 'django>=2.2'.",
    )
    our.add_argument(
        "--sitepackages",
        action="store_true",
        help="override sitepackages setting to True in all envs",
    )
    our.add_argument(
        "--alwayscopy",
        action="store_true",
        help="override alwayscopy setting to True in all envs",
    )


def legacy(state: State) -> int:
    option = state.options
    if option.show_config:
        state.options.list_keys_only = []
        state.options.show_core = True
        return show_config(state)
    if option.list_envs or option.list_envs_all:
        option.list_no_description = option.verbosity <= DEFAULT_VERBOSITY
        option.list_default_only = not option.list_envs_all
        option.show_core = False
        return list_env(state)
    if option.devenv_path:
        option.devenv_path = Path(option.devenv_path)
        return devenv(state)
    if option.parallel != 0:  # only 0 means sequential
        return run_parallel(state)
    return run_sequential(state)
