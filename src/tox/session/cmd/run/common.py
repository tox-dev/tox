"""Common functionality shared across multiple type of runs"""
import logging
import os
import time
from argparse import Action, ArgumentParser, ArgumentTypeError, Namespace
from concurrent.futures import CancelledError, Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from signal import SIGINT, Handlers, signal
from threading import Event, Thread
from typing import Any, Dict, Iterator, List, Optional, Sequence, Set, Tuple, Union, cast

from colorama import Fore

from tox.config.types import EnvList
from tox.execute import Outcome
from tox.journal import write_journal
from tox.session.cmd.run.single import ToxEnvRunResult, run_one
from tox.session.state import State
from tox.tox_env.api import ToxEnv
from tox.tox_env.errors import Skip
from tox.tox_env.runner import RunToxEnv
from tox.util.graph import stable_topological_sort
from tox.util.spinner import MISS_DURATION, Spinner


class SkipMissingInterpreterAction(Action):
    def __call__(
        self,
        parser: ArgumentParser,  # noqa
        args: Namespace,
        values: Union[str, Sequence[Any], None],
        option_string: Optional[str] = None,
    ) -> None:
        value = "true" if values is None else values
        if value not in ("config", "true", "false"):
            raise ArgumentTypeError(f"value must be 'config', 'true', or 'false' (got {repr(value)})")
        setattr(args, self.dest, value)


def env_run_create_flags(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--result-json",
        dest="result_json",
        metavar="path",
        of_type=Path,
        default=None,
        help="write a json file with detailed information about all commands and results involved",
    )
    parser.add_argument(
        "-s",
        "--skip-missing-interpreters",
        default="config",
        metavar="v",
        nargs="?",
        action=SkipMissingInterpreterAction,
        help="don't fail tests for missing interpreters: {config,true,false} choice",
    )
    parser.add_argument(
        "-r",
        "--recreate",
        dest="recreate",
        help="recreate the tox environments",
        action="store_true",
    )
    parser.add_argument(
        "-n",
        "--notest",
        dest="no_test",
        help="do not run the test commands",
        action="store_true",
    )
    parser.add_argument(
        "-b",
        "--pkg-only",
        "--sdistonly",
        action="store_true",
        help="only perform the packaging activity",
        dest="package_only",
    )
    parser.add_argument(
        "--installpkg",
        help="use specified package for installation into venv, instead of creating an sdist.",
        default=None,
        of_type=Path,
    )
    parser.add_argument(
        "--develop",
        action="store_true",
        help="install package in develop mode",
        dest="develop",
    )
    parser.add_argument(
        "--hashseed",
        metavar="SEED",
        help="set PYTHONHASHSEED to SEED before running commands. Defaults to a random integer in the range "
        "[1, 4294967295] ([1, 1024] on Windows). Passing 'noset' suppresses this behavior.",
        type=str,
        default="noset",
    )
    parser.add_argument(
        "--discover",
        dest="discover",
        nargs="+",
        metavar="path",
        help="for python discovery first try the python executables under these paths",
        default=[],
    )
    parser.add_argument(
        "--no-recreate-pkg",
        dest="no_recreate_pkg",
        help="if recreate is set do not recreate packaging tox environment(s)",
        action="store_true",
    )
    parser.add_argument(
        "--skip-pkg-install",
        dest="skip_pkg_install",
        help="skip package installation for this run",
        action="store_true",
    )


def run_and_report(state: State, result: List[ToxEnvRunResult]) -> int:
    # manifest the results
    name_to_run = {r.name: r for r in result}
    runs = [name_to_run[n] for n in list(state.env_list(everything=False))]
    # write the journal
    write_journal(getattr(state.options, "result_json", None), state.journal)
    # report the outcome
    return report(state.options.start, runs, state.options.is_colored)


def report(start: float, runs: List[ToxEnvRunResult], is_colored: bool) -> int:
    def _print(color: int, message: str) -> None:
        print(f"{color if is_colored else ''}{message}{Fore.RESET if is_colored else ''}")

    end = time.monotonic()
    all_ok = True
    for run in runs:
        ok = run.code == Outcome.OK
        msg = ("SKIP" if run.skipped else "OK") if ok else f"FAIL code {run.code}"
        duration_individual = [o.elapsed for o in run.outcomes]
        extra = f"+cmd[{','.join(f'{i:.2f}' for i in duration_individual)}]" if len(duration_individual) else ""
        setup = run.duration - sum(duration_individual)
        out = f"  {run.name}: {msg} ({run.duration:.2f}{f'=setup[{setup:.2f}]{extra}' if extra else ''} seconds)"
        _print((Fore.YELLOW if run.skipped else Fore.GREEN) if ok else Fore.RED, out)
        all_ok = ok and all_ok
    duration = end - start
    if all_ok:
        _print(Fore.GREEN, f"  congratulations :) ({duration:.2f} seconds)")
        return Outcome.OK
    else:
        _print(Fore.RED, f"  evaluation failed :( ({duration:.2f} seconds)")
        return runs[0].code if len(runs) == 1 else -1


logger = logging.getLogger(__name__)


def execute(state: State, max_workers: Optional[int], spinner: bool, live: bool) -> int:
    interrupt, done = Event(), Event()
    results: List[ToxEnvRunResult] = []
    future_to_env: Dict["Future[ToxEnvRunResult]", ToxEnv] = {}
    for env in list(state.env_list()):  # ensure envs can be constructed
        state.tox_env(env)
    previous, has_previous = None, False
    try:
        try:
            thread = Thread(
                target=_queue_and_wait,
                name="tox-interrupt",
                args=(state, results, future_to_env, interrupt, done, max_workers, spinner, live),
            )
            thread.start()
            thread.join()
        except KeyboardInterrupt:
            previous, has_previous = signal(SIGINT, Handlers.SIG_IGN), True
            logger.error(f"[{os.getpid()}] KeyboardInterrupt - teardown started")
            interrupt.set()
            for future, tox_env in list(future_to_env.items()):
                if future.cancel() is False and not future.done():  # if cannot be cancelled and not done -> still runs
                    tox_env.interrupt()
            done.wait()
    finally:
        exit_code = run_and_report(state, results)
        if has_previous:
            signal(SIGINT, previous)
        if "_TOX_SHOW_THREAD" in os.environ:  # pragma: no cover
            import threading  # pragma: no cover

            for thread in threading.enumerate():  # pragma: no cover
                print(thread)  # pragma: no cover
    return exit_code


class ToxSpinner(Spinner):
    def __init__(self, enabled: bool, state: State, total: int) -> None:
        super().__init__(
            enabled=enabled,
            colored=state.options.is_colored,
            stream=state.log_handler.stdout,
            total=total,
        )

    def update_spinner(self, result: ToxEnvRunResult, success: bool) -> None:
        if success:
            if result.skipped:
                done = self.skip
            else:
                done = self.succeed
        else:
            done = self.fail
        done(result.name)


def _queue_and_wait(
    state: State,
    results: List[ToxEnvRunResult],
    future_to_env: Dict["Future[ToxEnvRunResult]", ToxEnv],
    interrupt: Event,
    done: Event,
    max_workers: Optional[int],
    has_spinner: bool,
    live: bool,
) -> None:
    try:
        options = state.options
        to_run_list = list(state.env_list())
        with ToxSpinner(has_spinner, state, len(to_run_list)) as spinner:
            max_workers = len(to_run_list) if max_workers is None else max_workers
            completed: Set[str] = set()
            envs_to_run_generator = ready_to_run_envs(state, to_run_list, completed)

            def _run(tox_env: RunToxEnv) -> ToxEnvRunResult:
                spinner.add(tox_env.conf.name)
                return run_one(tox_env, options.recreate, options.no_test, suspend_display=live is False)

            try:
                executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="tox-driver")
                while True:
                    env_list: List[str] = next(envs_to_run_generator, [])
                    if not env_list and not future_to_env:
                        break

                    for env in env_list:  # queue all available
                        tox_env_to_run = state.tox_env(env)
                        if interrupt.is_set():  # queue the rest as failed upfront
                            tox_env_to_run.teardown()
                            future: "Future[ToxEnvRunResult]" = Future()
                            res = ToxEnvRunResult(name=env, skipped=False, code=-2, outcomes=[], duration=MISS_DURATION)
                            future.set_result(res)
                        else:
                            future = executor.submit(_run, tox_env_to_run)
                        future_to_env[future] = tox_env_to_run
                    future = next(as_completed(future_to_env))
                    tox_env_done = future_to_env.pop(future)
                    try:
                        result: ToxEnvRunResult = future.result()
                    except CancelledError:
                        tox_env_done.teardown()
                        name = tox_env_done.conf.name
                        result = ToxEnvRunResult(name=name, skipped=False, code=-3, outcomes=[], duration=MISS_DURATION)
                    results.append(result)
                    completed.add(result.name)
                    _handle_one_run_done(result, spinner, state, live)
            except BaseException:  # pragma: no cover # noqa
                logging.exception("Internal Error")  # pragma: no cover
                raise  # pragma: no cover
            finally:
                executor.shutdown(wait=True)
    finally:
        done.set()


def _handle_one_run_done(result: ToxEnvRunResult, spinner: ToxSpinner, state: State, live: bool) -> None:
    success = result.code == Outcome.OK
    spinner.update_spinner(result, success)
    if live is False and state.options.parallel_live is False:  # teardown background run
        tox_env = state.tox_env(result.name)
        out_err = tox_env.close_and_read_out_err()  # sync writes from buffer to stdout/stderr
        has_package = tox_env.package_env is not None
        pkg_out_err = tox_env.package_env.close_and_read_out_err() if has_package else None  # type: ignore
        if not success or tox_env.conf["parallel_show_output"]:
            if pkg_out_err is not None:  # pragma: no branch # first show package build
                state.log_handler.write_out_err(pkg_out_err)  # pragma: no cover
            if out_err is not None:  # pragma: no branch # first show package build
                state.log_handler.write_out_err(out_err)


def ready_to_run_envs(state: State, to_run: List[str], completed: Set[str]) -> Iterator[List[str]]:
    """Generate tox environments ready to run"""
    order, todo = run_order(state, to_run)
    at = 0
    while order:
        ready_to_run: List[str] = []
        new_order: List[str] = []
        for env in order:  # collect next batch of ready to run
            if todo[env] - completed:
                new_order.append(env)
            else:
                ready_to_run.append(env)
            at += 1
        order = new_order
        yield ready_to_run


def run_order(state: State, to_run: List[str]) -> Tuple[List[str], Dict[str, Set[str]]]:
    to_run_set = set(to_run)
    todo: Dict[str, Set[str]] = {}
    for env in to_run:
        try:
            run_env = state.tox_env(env)
        except Skip:
            continue
        depends = set(cast(EnvList, run_env.conf["depends"]).envs)
        todo[env] = to_run_set & depends
    order = stable_topological_sort(todo)
    return order, todo
