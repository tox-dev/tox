# mypy: ignore-errors
"""
Run tox environments in parallel.
"""
import logging
import os
from argparse import ArgumentParser, ArgumentTypeError
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from typing import Callable, Dict, Iterator, List, Set, Tuple, cast

from tox.config.cli.parser import ToxParser
from tox.config.types import EnvList
from tox.execute import Outcome
from tox.plugin.impl import impl
from tox.session.cmd.run.single import run_one
from tox.session.common import env_list_flag
from tox.session.state import State
from tox.util.cpu import auto_detect_cpus
from tox.util.graph import stable_topological_sort
from tox.util.spinner import Spinner

from .common import env_run_create_flags, run_and_report

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


def parse_num_processes(str_value):
    if str_value == "all":
        return None
    if str_value == "auto":
        return auto_detect_cpus()
    value = int(str_value)
    if value < 0:
        raise ArgumentTypeError("value must be positive")
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
    return run_and_report(state, _execute_parallel(state))


def _execute_parallel(state: State) -> Iterator[Tuple[str, Tuple[int, List[Outcome], float]]]:
    options = state.options
    live_out = options.parallel_live
    show_progress = not options.parallel_no_spinner and not live_out and options.verbosity > 2
    with Spinner(enabled=show_progress, colored=state.options.is_colored) as spinner:
        spinner_name_done: Callable[[str], None] = spinner.skip if options.no_test else spinner.succeed
        to_run_list = list(state.env_list())
        max_parallel = options.parallel
        executor = ThreadPoolExecutor(len(to_run_list) if max_parallel is None else max_parallel, "tox-parallel")
        try:
            future_to_name: Dict[Future, str] = {}
            completed: Set[str] = set()
            envs_to_run_generator = ready_to_run_envs(state, to_run_list, completed)
            while True:
                env_list = next(envs_to_run_generator, [])
                if not env_list and not future_to_name:
                    break
                for env in env_list:  # queue all available
                    spinner.add(env)
                    tox_env = state.tox_env(env)
                    if live_out is False:
                        tox_env.hide_display()
                    future = executor.submit(run_one, tox_env, options.recreate, options.no_test)
                    future_to_name[future] = env

                future = next(as_completed(future_to_name))
                name = future_to_name.pop(future)
                code, outcomes, duration = future.result()
                completed.add(name)
                if live_out is False:
                    state.tox_env(env).resume_display()
                (spinner_name_done if code == Outcome.OK else spinner.fail)(name)

                yield name, (code, outcomes, duration)
        except KeyboardInterrupt:
            logger.error(f"[{os.getpid()}] KeyboardInterrupt parallel - stopping children")
        executor.shutdown(wait=False)


def ready_to_run_envs(state: State, to_run: List[str], completed: Set[str]):
    """Generate tox environments ready to run"""
    to_run_set = set(to_run)
    todo: Dict[str, Set[str]] = {
        env: (to_run_set & set(cast(EnvList, state.tox_env(env).conf["depends"]).envs)) for env in to_run
    }
    order, at = stable_topological_sort(todo), 0
    while at != len(order):
        ready_to_run = []
        for env in order[at:]:  # collect next batch of ready to run
            if todo[env] - completed:
                break  # if not all dependencies completed, stop, topological order guarantees we're done
            ready_to_run.append(env)
            at += 1
        yield ready_to_run
