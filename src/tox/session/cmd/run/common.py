"""Common functionality shared across multiple type of runs"""
import logging
import os
import time
from argparse import Action, ArgumentError, ArgumentParser, Namespace
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
        namespace: Namespace,
        values: Union[str, Sequence[Any], None],
        option_string: Optional[str] = None,  # noqa: U100
    ) -> None:
        value = "true" if values is None else values
        if value not in ("config", "true", "false"):
            raise ArgumentError(self, f"value must be 'config', 'true', or 'false' (got {value!r})")
        setattr(namespace, self.dest, value)


class InstallPackageAction(Action):
    def __call__(
        self,
        parser: ArgumentParser,  # noqa
        namespace: Namespace,
        values: Union[str, Sequence[Any], None],
        option_string: Optional[str] = None,  # noqa: U100
    ) -> None:
        if not values:
            raise ArgumentError(self, "cannot be empty")
        path = Path(cast(str, values)).absolute()
        if not path.exists():
            raise ArgumentError(self, f"{path} does not exist")
        if not path.is_file():
            raise ArgumentError(self, f"{path} is not a file")
        setattr(namespace, self.dest, path)


def env_run_create_flags(parser: ArgumentParser, mode: str) -> None:
    # mode can be one of: run, run-parallel, legacy, devenv, config
    if mode != "config":
        parser.add_argument(
            "--result-json",
            dest="result_json",
            metavar="path",
            of_type=Path,
            default=None,
            help="write a JSON file with detailed information about all commands and results involved",
        )
    if mode != "devenv":
        parser.add_argument(
            "-s",
            "--skip-missing-interpreters",
            default="config",
            metavar="v",
            nargs="?",
            action=SkipMissingInterpreterAction,
            help="don't fail tests for missing interpreters: {config,true,false} choice",
        )
    if mode not in ("devenv", "config"):
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
            help="use specified package for installation into venv, instead of packaging the project",
            default=None,
            of_type=Optional[Path],
            action=InstallPackageAction,
            dest="install_pkg",
        )
    if mode != "devenv":
        parser.add_argument(
            "--develop",
            action="store_true",
            help="install package in development mode",
            dest="develop",
        )
    if mode != "config":
        parser.add_argument(
            "--hashseed",
            metavar="SEED",
            help="set PYTHONHASHSEED to SEED before running commands. Defaults to a random integer in the range "
            "[1, 4294967295] ([1, 1024] on Windows). Passing 'noset' suppresses this behavior.",
            type=str,
            default="noset",
            dest="hash_seed",
        )
    parser.add_argument(
        "--discover",
        dest="discover",
        nargs="+",
        metavar="path",
        help="for Python discovery first try the Python executables under these paths",
        default=[],
    )
    parser.add_argument(
        "--no-recreate-pkg",
        dest="no_recreate_pkg",
        help="if recreate is set do not recreate packaging tox environment(s)",
        action="store_true",
    )
    if mode not in ("devenv", "config"):
        parser.add_argument(
            "--skip-pkg-install",
            dest="skip_pkg_install",
            help="skip package installation for this run",
            action="store_true",
        )


def report(start: float, runs: List[ToxEnvRunResult], is_colored: bool) -> int:
    def _print(color_: int, message: str) -> None:
        print(f"{color_ if is_colored else ''}{message}{Fore.RESET if is_colored else ''}")

    all_good = True
    for run in runs:
        all_good &= run.code == Outcome.OK or run.ignore_outcome
        duration_individual = [o.elapsed for o in run.outcomes]
        extra = f"+cmd[{','.join(f'{i:.2f}' for i in duration_individual)}]" if duration_individual else ""
        setup = run.duration - sum(duration_individual)
        msg, color = _get_outcome_message(run)
        out = f"  {run.name}: {msg} ({run.duration:.2f}{f'=setup[{setup:.2f}]{extra}' if extra else ''} seconds)"
        _print(color, out)

    duration = time.monotonic() - start
    if all_good:
        _print(Fore.GREEN, f"  congratulations :) ({duration:.2f} seconds)")
        return Outcome.OK
    _print(Fore.RED, f"  evaluation failed :( ({duration:.2f} seconds)")
    return runs[0].code if len(runs) == 1 else -1


def _get_outcome_message(run: ToxEnvRunResult) -> Tuple[str, int]:
    if run.skipped:
        msg, color = "SKIP", Fore.YELLOW
    elif run.code == Outcome.OK:
        msg, color = "OK", Fore.GREEN
    else:
        if run.ignore_outcome:
            msg, color = f"IGNORED FAIL code {run.code}", Fore.YELLOW
        else:
            msg, color = f"FAIL code {run.code}", Fore.RED
    return msg, color


logger = logging.getLogger(__name__)


def execute(state: State, max_workers: Optional[int], has_spinner: bool, live: bool) -> int:
    interrupt, done = Event(), Event()
    results: List[ToxEnvRunResult] = []
    future_to_env: Dict["Future[ToxEnvRunResult]", ToxEnv] = {}
    to_run_list: List[str] = []
    for env in state.env_list():  # ensure envs can be constructed
        state.tox_env(env)
        to_run_list.append(env)
    previous, has_previous = None, False
    try:
        spinner = ToxSpinner(has_spinner, state, len(to_run_list))
        try:
            thread = Thread(
                target=_queue_and_wait,
                name="tox-interrupt",
                args=(state, to_run_list, results, future_to_env, interrupt, done, max_workers, spinner, live),
            )
            thread.start()
            thread.join()
        except KeyboardInterrupt:
            previous, has_previous = signal(SIGINT, Handlers.SIG_IGN), True
            spinner.print_report = False  # no need to print reports at this point, final report coming up
            logger.error(f"[{os.getpid()}] KeyboardInterrupt - teardown started")
            interrupt.set()
            for future, tox_env in list(future_to_env.items()):
                if future.cancel() is False and not future.done():  # if cannot be cancelled and not done -> still runs
                    tox_env.interrupt()
            done.wait()
    finally:
        ordered_results: List[ToxEnvRunResult] = []
        name_to_run = {r.name: r for r in results}
        for env in to_run_list:
            ordered_results.append(name_to_run[env])
        # write the journal
        write_journal(getattr(state.options, "result_json", None), state.journal)
        # report the outcome
        exit_code = report(state.options.start, ordered_results, state.options.is_colored)
        if has_previous:
            signal(SIGINT, previous)
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
            done = self.skip if result.skipped else self.succeed
        else:
            done = self.fail
        done(result.name)


def _queue_and_wait(
    state: State,
    to_run_list: List[str],
    results: List[ToxEnvRunResult],
    future_to_env: Dict["Future[ToxEnvRunResult]", ToxEnv],
    interrupt: Event,
    done: Event,
    max_workers: Optional[int],
    spinner: ToxSpinner,
    live: bool,
) -> None:
    try:
        options = state.options
        with spinner:
            max_workers = len(to_run_list) if max_workers is None else max_workers
            completed: Set[str] = set()
            envs_to_run_generator = ready_to_run_envs(state, to_run_list, completed)

            def _run(tox_env: RunToxEnv) -> ToxEnvRunResult:
                spinner.add(tox_env.conf.name)
                return run_one(tox_env, options.no_test, suspend_display=live is False)

            try:
                executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="tox-driver")
                env_list: List[str] = []
                while True:
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

                    if not future_to_env:
                        result: Optional[ToxEnvRunResult] = None
                    else:  # if we have queued wait for completed
                        future = next(as_completed(future_to_env))
                        tox_env_done = future_to_env.pop(future)
                        try:
                            result = future.result()
                        except CancelledError:
                            tox_env_done.teardown()
                            name = tox_env_done.conf.name
                            result = ToxEnvRunResult(
                                name=name, skipped=False, code=-3, outcomes=[], duration=MISS_DURATION
                            )
                        results.append(result)
                        completed.add(result.name)

                    env_list = next(envs_to_run_generator, [])
                    # if nothing running and nothing more to run we're done
                    final_run = not env_list and not future_to_env
                    if final_run:  # disable report on final env
                        spinner.print_report = False
                    if result is not None:
                        _handle_one_run_done(result, spinner, state, live)
                    if final_run:
                        break

            except BaseException:  # pragma: no cover # noqa
                logging.exception("Internal Error")  # pragma: no cover
                raise  # pragma: no cover
            finally:
                executor.shutdown(wait=True)
    finally:
        try:
            # call teardown - configuration only environments for example could not be finished
            for _, tox_env in state.run_envs():
                tox_env.teardown()
        finally:
            done.set()


def _handle_one_run_done(result: ToxEnvRunResult, spinner: ToxSpinner, state: State, live: bool) -> None:
    success = result.code == Outcome.OK
    spinner.update_spinner(result, success)
    tox_env = state.tox_env(result.name)
    if tox_env.journal:  # add overall journal entry
        tox_env.journal["result"] = {
            "success": success,
            "exit_code": result.code,
            "duration": result.duration,
        }
    if live is False and state.options.parallel_live is False:  # teardown background run
        out_err = tox_env.close_and_read_out_err()  # sync writes from buffer to stdout/stderr
        pkg_out_err_list = []
        for package_env in tox_env.package_envs:
            pkg_out_err = package_env.close_and_read_out_err()
            if pkg_out_err is not None:  # pragma: no branch
                pkg_out_err_list.append(pkg_out_err)
        if not success or tox_env.conf["parallel_show_output"]:
            for pkg_out_err in pkg_out_err_list:
                state.log_handler.write_out_err(pkg_out_err)  # pragma: no cover
            if out_err is not None:  # pragma: no branch # first show package build
                state.log_handler.write_out_err(out_err)


def ready_to_run_envs(state: State, to_run: List[str], completed: Set[str]) -> Iterator[List[str]]:
    """Generate tox environments ready to run"""
    order, todo = run_order(state, to_run)
    while order:
        ready_to_run: List[str] = []
        new_order: List[str] = []
        for env in order:  # collect next batch of ready to run
            if todo[env] - completed:
                new_order.append(env)
            else:
                ready_to_run.append(env)
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
