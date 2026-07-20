"""Common functionality shared across multiple type of runs."""

from __future__ import annotations

import logging
import os
import time
from argparse import Action, ArgumentError, ArgumentParser, Namespace
from concurrent.futures import FIRST_COMPLETED, CancelledError, Future, ThreadPoolExecutor
from concurrent.futures import wait as wait_futures
from fnmatch import fnmatchcase
from pathlib import Path
from signal import SIGINT, Handlers, signal
from threading import Event, Thread
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

from colorama import Fore

from tox.execute import Outcome
from tox.journal import write_journal
from tox.report import HandledError
from tox.session.cmd.run.single import ToxEnvRunResult, run_one
from tox.util.graph import stable_topological_sort
from tox.util.spinner import MISS_DURATION, Spinner

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from tox.config.types import EnvList
    from tox.session.state import State
    from tox.tox_env.api import ToxEnv
    from tox.tox_env.runner import RunToxEnv


class SkipMissingInterpreterAction(Action):
    def __call__(
        self,
        parser: ArgumentParser,  # ruff:ignore[unused-method-argument]
        namespace: Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,  # ruff:ignore[unused-method-argument]
    ) -> None:
        value = "true" if values is None else values
        if value not in {"config", "true", "false"}:
            raise ArgumentError(self, f"value must be 'config', 'true', or 'false' (got {value!r})")
        setattr(namespace, self.dest, value)


class InstallPackageAction(Action):
    def __call__(
        self,
        parser: ArgumentParser,  # ruff:ignore[unused-method-argument]
        namespace: Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,  # ruff:ignore[unused-method-argument]
    ) -> None:
        if not values:
            raise ArgumentError(self, "cannot be empty")
        raw = cast("str", values)
        path = self._resolve_path(raw)
        if not path.exists():
            raise ArgumentError(self, f"{path} does not exist")
        if not path.is_file():
            raise ArgumentError(self, f"{path} is not a file")
        setattr(namespace, self.dest, path)

    @staticmethod
    def _resolve_path(raw: str) -> Path:
        """Convert a raw string (possibly a ``file:`` URI) to an absolute :class:`~pathlib.Path`."""
        if raw.startswith("file:"):
            parsed = urlparse(raw)
            path = Path(url2pathname(unquote(parsed.path)))
        else:
            path = Path(raw)
        return path.absolute()


def env_run_create_flags(parser: ArgumentParser, mode: str) -> None:
    # mode can be one of: run, run-parallel, legacy, devenv, config
    if mode not in {"devenv", "depends"}:
        parser.add_argument(
            "-s",
            "--skip-missing-interpreters",
            default="config",
            metavar="v",
            nargs="?",
            action=SkipMissingInterpreterAction,
            help="don't fail tests for missing interpreters: {config,true,false} choice",
        )
    if mode not in {"devenv", "config", "depends"}:
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
            of_type=Path | None,
            action=InstallPackageAction,
            dest="install_pkg",
        )
        parser.add_argument(
            "--fail-fast",
            action="store_true",
            default=False,
            dest="fail_fast",
            help="stop execution after the first environment failure",
        )
    if mode not in {"devenv", "depends"}:
        parser.add_argument(
            "--develop",
            action="store_true",
            help="install package in development mode",
            dest="develop",
        )
    if mode != "depends":
        parser.add_argument(
            "--no-recreate-pkg",
            dest="no_recreate_pkg",
            help="if recreate is set do not recreate packaging tox environment(s)",
            action="store_true",
        )
    if mode not in {"devenv", "config", "depends"}:
        parser.add_argument(
            "--skip-pkg-install",
            dest="skip_pkg_install",
            help="skip package installation for this run",
            action="store_true",
        )
        parser.add_argument(
            "--skip-env-install",
            dest="skip_env_install",
            help="skip dependency and package installation, reuse existing environment",
            action="store_true",
        )


def report(start: float, runs: list[ToxEnvRunResult], is_colored: bool, verbosity: int) -> int:  # ruff:ignore[boolean-type-hint-positional-argument]
    def _print(color_: int, message: str) -> None:
        if verbosity:
            print(f"{color_ if is_colored else ''}{message}{Fore.RESET if is_colored else ''}")  # ruff:ignore[print]

    successful, skipped = [], []
    for run in runs:
        successful.append(run.code == Outcome.OK or run.ignore_outcome or run.unavailable)
        skipped.append(run.skipped)
        duration_individual = [o.elapsed for o in run.outcomes] if verbosity >= 2 else []  # ruff:ignore[magic-value-comparison]
        extra = f"+cmd[{','.join(f'{i:.2f}' for i in duration_individual)}]" if duration_individual else ""
        setup = run.duration - sum(duration_individual)
        msg, color = _get_outcome_message(run)
        out = f"  {run.name}: {msg} ({run.duration:.2f}{f'=setup[{setup:.2f}]{extra}' if extra else ''} seconds)"
        _print(color, out)

    duration = time.monotonic() - start
    all_good = all(successful) and not all(skipped)
    if all_good:
        _print(Fore.GREEN, f"  congratulations :) ({duration:.2f} seconds)")
        return Outcome.OK
    _print(Fore.RED, f"  evaluation failed :( ({duration:.2f} seconds)")
    if len(runs) == 1:
        return runs[0].code if not runs[0].skipped else 1
    return 1


def _get_outcome_message(run: ToxEnvRunResult) -> tuple[str, int]:
    if run.unavailable:
        msg, color = "NOT AVAILABLE", Fore.YELLOW
    elif run.skipped:
        msg, color = "SKIP", Fore.YELLOW
    elif run.code == Outcome.OK:
        msg, color = "OK", Fore.GREEN
    elif run.ignore_outcome:
        msg, color = f"IGNORED FAIL code {run.code}", Fore.YELLOW
    else:
        msg, color = f"FAIL code {run.code}", Fore.RED
    return msg, color


logger = logging.getLogger(__name__)


def _warn_unused_config(state: State) -> None:
    from tox.config.cli.parser import DEFAULT_VERBOSITY  # ruff:ignore[import-outside-top-level]

    if state.conf.options.verbosity <= DEFAULT_VERBOSITY:
        return
    is_colored = state.conf.options.is_colored
    for name in state.envs.iter():
        if unused := state.envs[name].conf.unused():
            _print_unused(is_colored, f"[testenv:{name}]", unused)
    if unused := state.conf.core.unused():
        _print_unused(is_colored, "[tox]", unused)


def _print_unused(is_colored: bool, section: str, unused: list[str]) -> None:  # ruff:ignore[boolean-type-hint-positional-argument]
    msg = f"  {section} unused config key(s): {', '.join(unused)}"
    print(f"{Fore.YELLOW if is_colored else ''}{msg}{Fore.RESET if is_colored else ''}")  # ruff:ignore[print]


def execute(state: State, max_workers: int | None, has_spinner: bool, live: bool) -> int:  # ruff:ignore[boolean-type-hint-positional-argument]
    interrupt, done = Event(), Event()
    results: list[ToxEnvRunResult] = []
    future_to_env: dict[Future[ToxEnvRunResult], ToxEnv] = {}
    state.envs.ensure_only_run_env_is_active()
    to_run_list: list[str] = list(state.envs.iter())
    for name in to_run_list:
        cast("RunToxEnv", state.envs[name]).mark_active()

    scheduler_error: list[BaseException] = []

    def _run_thread() -> tuple[Any, bool]:
        spinner = ToxSpinner(has_spinner, state, len(to_run_list))
        thread = Thread(
            target=_queue_and_wait,
            name="tox-interrupt",
            args=(
                state,
                to_run_list,
                results,
                future_to_env,
                interrupt,
                done,
                max_workers,
                spinner,
                live,
                scheduler_error,
            ),
        )
        thread.start()
        try:
            while thread.is_alive():
                thread.join(timeout=1)
        except KeyboardInterrupt:
            previous = signal(SIGINT, Handlers.SIG_IGN)
            spinner.print_report = False  # no need to print reports at this point, final report coming up
            logger.error("[%s] KeyboardInterrupt - teardown started", os.getpid())  # ruff:ignore[error-instead-of-exception]
            interrupt.set()
            # cancel in reverse order to not allow submitting new jobs as we cancel running ones
            for future, tox_env in reversed(list(future_to_env.items())):
                canceled = future.cancel()
                # if cannot be canceled and not done -> still runs
                if canceled is False and not future.done():  # pragma: no branch
                    tox_env.interrupt()
            done.wait()
            thread.join()
            return previous, True
        return None, False

    previous, has_previous = None, False
    try:
        previous, has_previous = _run_thread()
        if scheduler_error:
            raise scheduler_error[0]
    finally:
        ordered_results = _order_results(state, results, to_run_list)
        # write the journal
        write_journal(getattr(state.conf.options, "result_json", None), state._journal)  # ruff:ignore[private-member-access]
        # warn about unused config keys
        _warn_unused_config(state)
        # report the outcome
        exit_code = report(
            state.conf.options.start,
            ordered_results,
            state.conf.options.is_colored,
            state.conf.options.verbosity,
        )
        if has_previous:
            signal(SIGINT, previous)
    return exit_code


def _order_results(state: State, results: list[ToxEnvRunResult], to_run_list: list[str]) -> list[ToxEnvRunResult]:
    name_to_run = {r.name: r for r in results}
    ordered: list[ToxEnvRunResult] = [
        name_to_run.get(env, ToxEnvRunResult(name=env, skipped=True, code=-2, outcomes=[], duration=MISS_DURATION))
        for env in to_run_list
    ]
    # add results for unavailable environments
    ordered.extend(
        ToxEnvRunResult(name=env_name, skipped=False, code=0, outcomes=[], duration=MISS_DURATION, unavailable=True)
        for env_name in state.envs.unavailable_envs()
        if env_name not in name_to_run
    )
    return ordered


class ToxSpinner(Spinner):
    def __init__(self, enabled: bool, state: State, total: int) -> None:  # ruff:ignore[boolean-type-hint-positional-argument]
        super().__init__(
            enabled=enabled,
            colored=state.conf.options.is_colored,
            stream=state._options.log_handler.stdout,  # ruff:ignore[private-member-access]
            total=total,
        )

    def update_spinner(self, result: ToxEnvRunResult, success: bool) -> None:  # ruff:ignore[boolean-type-hint-positional-argument]
        done = (self.skip if result.skipped else self.succeed) if success else self.fail
        done(result.name)


def _next_completed(
    future_to_env: dict[Future[ToxEnvRunResult], ToxEnv],
    interrupt: Event,
) -> Future[ToxEnvRunResult] | None:
    while True:
        done_futures, _ = wait_futures(list(future_to_env), timeout=1, return_when=FIRST_COMPLETED)
        if done_futures:
            return done_futures.pop()
        if interrupt.is_set():
            return None


def _queue_and_wait(  # ruff:ignore[too-many-arguments]
    state: State,
    to_run_list: list[str],
    results: list[ToxEnvRunResult],
    future_to_env: dict[Future[ToxEnvRunResult], ToxEnv],
    interrupt: Event,
    done: Event,
    max_workers: int | None,
    spinner: ToxSpinner,
    live: bool,  # ruff:ignore[boolean-type-hint-positional-argument]
    error: list[BaseException],
) -> None:
    try:
        try:
            _do_queue_and_wait(state, to_run_list, results, future_to_env, interrupt, max_workers, spinner, live)
        except BaseException as exception:  # ruff:ignore[blind-except] # re-raised in the main thread
            error.append(exception)
    finally:
        try:
            for name in to_run_list:
                state.envs[name].teardown()
        finally:
            done.set()


def _do_queue_and_wait(  # ruff:ignore[complex-structure, too-many-arguments, too-many-statements, too-many-branches]
    state: State,
    to_run_list: list[str],
    results: list[ToxEnvRunResult],
    future_to_env: dict[Future[ToxEnvRunResult], ToxEnv],
    interrupt: Event,
    max_workers: int | None,
    spinner: ToxSpinner,
    live: bool,  # ruff:ignore[boolean-type-hint-positional-argument]
) -> None:
    options = state._options  # ruff:ignore[private-member-access]
    with spinner:  # ruff:ignore[too-many-nested-blocks]
        # an unbounded pool (-p all) sizes to the selection; keep at least one worker so an empty
        # selection does not raise ValueError from ThreadPoolExecutor
        max_workers = max(1, len(to_run_list)) if max_workers is None else max_workers
        completed: set[str] = set()
        envs_to_run_generator = ready_to_run_envs(state, to_run_list, completed)

        def _run(tox_env: RunToxEnv) -> ToxEnvRunResult:
            spinner.add(tox_env.conf.name)
            return run_one(
                tox_env,
                options.parsed.no_test or options.parsed.package_only,
                suspend_display=live is False,
            )

        env_list: list[str] = []
        fail_fast_enabled = options.parsed.fail_fast or any(
            cast("RunToxEnv", state.envs[env]).conf["fail_fast"] for env in to_run_list
        )
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="tox-driver") as executor:
            while True:
                envs_to_queue = (
                    env_list[:1] if max_workers == 1 and fail_fast_enabled and not interrupt.is_set() else env_list
                )
                for env in envs_to_queue:  # queue all available (or one at a time if sequential + fail-fast)
                    tox_env_to_run = cast("RunToxEnv", state.envs[env])
                    if interrupt.is_set():  # queue the rest as failed upfront
                        tox_env_to_run.teardown()
                        future: Future[ToxEnvRunResult] = Future()
                        res = ToxEnvRunResult(name=env, skipped=False, code=-2, outcomes=[], duration=MISS_DURATION)
                        future.set_result(res)
                    else:
                        future = executor.submit(_run, tox_env_to_run)
                    future_to_env[future] = tox_env_to_run
                env_list = env_list[len(envs_to_queue) :]

                if not future_to_env:
                    result: ToxEnvRunResult | None = None
                else:
                    completed_future = _next_completed(future_to_env, interrupt)
                    if completed_future is None:
                        for pending_future, pending_env in list(future_to_env.items()):
                            if not pending_future.cancel() and not pending_future.done():
                                pending_env.interrupt()
                        future_to_env.clear()
                        env_list = []
                        result = None
                    else:
                        tox_env_done = future_to_env.pop(completed_future)
                        try:
                            result = completed_future.result()
                        except CancelledError:
                            tox_env_done.teardown()
                            name = tox_env_done.conf.name
                            result = ToxEnvRunResult(
                                name=name,
                                skipped=False,
                                code=-3,
                                outcomes=[],
                                duration=MISS_DURATION,
                            )
                        results.append(result)
                        completed.add(result.name)
                        if (
                            result.code != Outcome.OK
                            and not result.ignore_outcome
                            and (options.parsed.fail_fast or result.fail_fast)
                        ):
                            interrupt.set()
                            env_list = []
                            for pending_future in list(future_to_env.keys()):
                                pending_future.cancel()

                if not interrupt.is_set() and not env_list:
                    env_list = next(envs_to_run_generator, [])
                # if nothing running and nothing more to run we're done
                final_run = not env_list and not future_to_env
                if final_run:  # disable report on final env
                    spinner.print_report = False
                if result is not None:
                    _handle_one_run_done(result, spinner, state, live)
                if final_run:
                    break


def _handle_one_run_done(
    result: ToxEnvRunResult,
    spinner: ToxSpinner,
    state: State,
    live: bool,  # ruff:ignore[boolean-type-hint-positional-argument]
) -> None:
    success = result.code == Outcome.OK
    spinner.update_spinner(result, success)
    tox_env = cast("RunToxEnv", state.envs[result.name])
    if tox_env.journal:  # add overall journal entry
        tox_env.journal["result"] = {
            "success": success,
            "exit_code": result.code,
            "duration": result.duration,
        }
    if live is False and state.conf.options.parallel_live is False:  # teardown background run
        out_err = tox_env.close_and_read_out_err()  # sync writes from buffer to stdout/stderr
        pkg_out_err_list = []
        for package_env in tox_env.package_envs:
            pkg_out_err = package_env.close_and_read_out_err()
            if pkg_out_err is not None:  # pragma: no branch
                pkg_out_err_list.append(pkg_out_err)
        if not success or tox_env.conf["parallel_show_output"] or state.conf.options.list_dependencies:
            for pkg_out_err in pkg_out_err_list:
                state._options.log_handler.write_out_err(pkg_out_err)  # pragma: no cover  # ruff:ignore[private-member-access]
            if out_err is not None:  # pragma: no branch # first show package build
                state._options.log_handler.write_out_err(out_err)  # ruff:ignore[private-member-access]


def ready_to_run_envs(state: State, to_run: list[str], completed: set[str]) -> Iterator[list[str]]:
    """Generate tox environments ready to run."""
    order, todo = run_order(state, to_run)
    while order:
        ready_to_run: list[str] = []
        new_order: list[str] = []
        for env in order:  # collect next batch of ready to run
            if todo[env] - completed:
                new_order.append(env)
            else:
                ready_to_run.append(env)
        order = new_order
        yield ready_to_run


def run_order(state: State, to_run: list[str]) -> tuple[list[str], dict[str, set[str]]]:
    to_run_set = set(to_run)
    todo: dict[str, set[str]] = {}
    for env in to_run:
        run_env = cast("RunToxEnv", state.envs[env])
        depends = set(cast("EnvList", run_env.conf["depends"]).envs)
        todo[env] = {name for dep in depends for name in to_run_set if fnmatchcase(name, dep)} - {env}
    try:
        order = stable_topological_sort(todo)
    except ValueError as exception:
        msg = f"circular dependency detected between environments: {exception}"
        raise HandledError(msg) from exception
    return order, todo
