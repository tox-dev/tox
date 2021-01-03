"""
Run tox environments in parallel.
"""
import logging
from argparse import ArgumentParser, ArgumentTypeError
from typing import Optional

from tox.config.cli.parser import ToxParser
from tox.plugin.impl import impl
from tox.session.common import env_list_flag
from tox.session.state import State
from tox.util.cpu import auto_detect_cpus

from .common import env_run_create_flags, execute

logger = logging.getLogger(__name__)

ENV_VAR_KEY = "TOX_PARALLEL_ENV"
OFF_VALUE = 0
DEFAULT_PARALLEL = OFF_VALUE


@impl
def tox_add_option(parser: ToxParser) -> None:
    our = parser.add_command("run-parallel", ["p"], "run environments in parallel", run_parallel)
    env_list_flag(our)
    env_run_create_flags(our)
    parallel_flags(our, default_parallel=auto_detect_cpus())


def parse_num_processes(str_value: str) -> Optional[int]:
    if str_value == "all":
        return None
    if str_value == "auto":
        return auto_detect_cpus()
    try:
        value = int(str_value)
    except ValueError as exc:
        raise ArgumentTypeError(f"value must be a positive number, is {str_value}") from exc
    if value < 0:
        raise ArgumentTypeError(f"value must be positive, is {value}")
    return value


def parallel_flags(our: ArgumentParser, default_parallel: int) -> None:
    our.add_argument(
        "-p",
        "--parallel",
        dest="parallel",
        help="run tox environments in parallel, the argument controls limit: all,"
        " auto - cpu count, some positive number, zero is turn off",
        action="store",
        type=parse_num_processes,
        default=default_parallel,
        metavar="VAL",
    )
    our.add_argument(
        "-o",
        "--parallel-live",
        action="store_true",
        dest="parallel_live",
        help="connect to stdout while running environments",
    )
    our.add_argument(
        "--parallel-no-spinner",
        action="store_true",
        dest="parallel_no_spinner",
        help="do not show the spinner",
    )


def run_parallel(state: State) -> int:
    """here we'll just start parallel sub-processes"""
    return execute(
        state,
        max_workers=state.options.parallel,
        spinner=state.options.parallel_no_spinner is False and state.options.parallel_live is False,
        live=state.options.parallel_live,
    )
