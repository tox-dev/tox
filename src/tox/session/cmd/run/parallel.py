"""Run tox environments in parallel."""

from __future__ import annotations

import logging
from argparse import ArgumentParser, ArgumentTypeError
from typing import TYPE_CHECKING, Final

from tox.plugin import impl
from tox.session.env_select import CliEnv, register_env_select_flags
from tox.util.ci import is_ci
from tox.util.cpu import auto_detect_cpus

from .common import env_run_create_flags, execute

if TYPE_CHECKING:
    from tox.config.cli.parser import ToxParser
    from tox.session.state import State

LOGGER: Final[logging.Logger] = logging.getLogger(__name__)
"""Logger of the parallel run."""

ENV_VAR_KEY: Final[str] = "TOX_PARALLEL_ENV"
"""Environment variable that tells a parallel sub-process which environment it runs."""
OFF_VALUE: Final[int] = 0
"""Value of the parallel option that turns parallel runs off."""
DEFAULT_PARALLEL: Final[str] = "auto"
"""Default value of the parallel option, ``auto`` for one process per CPU."""


@impl
def tox_add_option(parser: ToxParser) -> None:
    """Add the ``run-parallel`` sub-command to the command line parser.

    :param parser: the parser to add the sub-command to
    """
    our = parser.add_command("run-parallel", ["p"], "run environments in parallel", run_parallel)
    register_env_select_flags(our, default=CliEnv())
    env_run_create_flags(our, mode="run-parallel")
    parallel_flags(our, default_parallel=DEFAULT_PARALLEL)


def run_parallel(state: State) -> int:
    """Here we'll just start parallel sub-processes.

    :param state: the state of the run

    :returns: the exit code of the run

    :raises SystemExit: when the run is interrupted

    """
    option = state.conf.options
    if option.no_capture:
        msg = "--no-capture cannot be used with parallel mode"
        raise SystemExit(msg)
    return execute(
        state,
        max_workers=1 if option.parallel == OFF_VALUE else option.parallel,
        has_spinner=option.parallel_no_spinner is False and option.parallel_live is False,
        live=option.parallel_live,
    )


def parallel_flags(
    our: ArgumentParser,
    default_parallel: int | str,
    # keeps the existing signature
    no_args: bool = False,  # ruff:ignore[boolean-type-hint-positional-argument, boolean-default-value-positional-argument]
) -> None:
    """Add the flags that control how many environments run in parallel.

    :param our: the parser to add the flags to
    :param default_parallel: the number of parallel processes when the flag is not given
    :param no_args: whether the parallel flag can be given without a value
    """
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
        nargs="?" if no_args else None,
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
        default=is_ci(),
        help="disable the spinner when running in parallel, enabled by default in CI",
    )


def parse_num_processes(str_value: str) -> int | None:
    """Parse the number of parallel processes from a command line value.

    :param str_value: the value, ``all`` for no limit, ``auto`` for one process per CPU, or a number

    :returns: the number of processes, ``None`` for no limit

    :raises ArgumentTypeError: when the value is neither of those, or is negative
    """
    if str_value == "all":
        return None
    if str_value == "auto":
        return auto_detect_cpus()
    try:
        value = int(str_value)
    except ValueError as exc:
        msg = f"value must be a positive number, is {str_value!r}"
        raise ArgumentTypeError(msg) from exc
    if value < 0:
        msg = f"value must be positive, is {value!r}"
        raise ArgumentTypeError(msg)
    return value
