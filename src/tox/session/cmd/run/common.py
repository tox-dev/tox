"""Shared run behavior."""  # simplint: ignore[catch-all-module]  # used across run commands

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
from typing import TYPE_CHECKING, Any, Final, Literal, cast
from urllib.parse import urlparse
from urllib.request import url2pathname

from colorama import Fore

from tox.config.cli.parser import DEFAULT_VERBOSITY
from tox.config.types import EnvList
from tox.execute import Outcome
from tox.journal import write_journal
from tox.report import HandledError
from tox.tox_env.errors import Fail
from tox.util.graph import stable_topological_sort
from tox.util.spinner import MISS_DURATION, Spinner
from tox.util.typing_compat import override
from tox.util.venv_redirect import record_venv_redirect, venv_redirect_path

from .single import ToxEnvRunResult, run_one

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Sequence
    from types import FrameType

    from tox.session.state import State
    from tox.tox_env.api import ToxEnv
    from tox.tox_env.runner import RunToxEnv


def env_run_create_flags(
    parser: ArgumentParser, mode: Literal["run", "run-parallel", "legacy", "devenv", "config", "depends", "exec"]
) -> None:
    """Add the flags that control how the environments of a run are created.

    :param parser: the parser to add the flags to
    :param mode: the command the flags are added for

    """
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


class SkipMissingInterpreterAction(Action):
    """Set how missing interpreters are handled, from the value given to ``--skip-missing-interpreters``."""

    @override
    def __call__(
        self,
        parser: ArgumentParser,
        namespace: Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ) -> None:
        value = "true" if values is None else values
        if value not in {"config", "true", "false"}:
            raise ArgumentError(self, f"value must be 'config', 'true', or 'false' (got {value!r})")
        setattr(namespace, self.dest, value)


class InstallPackageAction(Action):
    """Store the path of a package file given on the command line, after checking that it is a file."""

    @override
    def __call__(
        self,
        parser: ArgumentParser,
        namespace: Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ) -> None:
        if not values:
            raise ArgumentError(self, "cannot be empty")
        path = self._resolve_path(cast("str", values))
        if not path.exists():
            raise ArgumentError(self, f"{path} does not exist")
        if not path.is_file():
            raise ArgumentError(self, f"{path} is not a file")
        setattr(namespace, self.dest, path)

    @staticmethod
    def _resolve_path(raw: str) -> Path:
        # Convert a raw string (possibly a ``file:`` URI) to an absolute :class:`~pathlib.Path`.
        return (Path(url2pathname(urlparse(raw).path)) if raw.startswith("file:") else Path(raw)).absolute()

    def normalize_default(self, value: Path) -> Path:
        """Resolve the default value the same way as a value given on the command line.

        :param value: the default value

        :returns: the resolved path

        """
        return self._resolve_path(value.as_posix())


_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


def execute(  # keeps the signature
    state: State,
    max_workers: int | None,
    has_spinner: bool,  # ruff:ignore[boolean-type-hint-positional-argument]  # keeps the signature
    live: bool,  # ruff:ignore[boolean-type-hint-positional-argument]  # keeps the signature
) -> int:
    """Run the selected environments, with a limit on how many run at the same time.

    :param state: the state of the run
    :param max_workers: the maximum number of environments that run at the same time, ``None`` for no limit
    :param has_spinner: whether to show a spinner while the environments run
    :param live: whether to show the output of the environments as it is produced

    :returns: the exit code

    """
    interrupt, done = Event(), Event()
    results: list[ToxEnvRunResult] = []
    future_to_env: dict[Future[ToxEnvRunResult], ToxEnv] = {}
    state.envs.ensure_only_run_env_is_active()
    to_run_list: list[str] = list(state.envs.iter())
    for name in to_run_list:
        cast("RunToxEnv", state.envs[name]).mark_active()
    _venv_redirect_enabled(state, _env_dirs(state))  # reject a conflicting setting before any environment runs

    scheduler_error: list[BaseException] = []

    def _run_thread() -> tuple[
        Callable[
            [int, FrameType | None], Any  # simplint: ignore[imprecise-annotation]  # signal handlers return any value
        ]
        | int
        | Handlers
        | None,
        bool,
    ]:
        spinner = _ToxSpinner(has_spinner, state, len(to_run_list))
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
            _LOGGER.error(  # ruff:ignore[error-instead-of-exception]  # expected error log
                "[%s] KeyboardInterrupt - teardown started", os.getpid()
            )
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
        write_journal(state.conf.options.result_json, state._journal)  # ruff:ignore[private-member-access]
        # let editors discover an environment
        _record_venv_redirect(state)
        # warn about unused config keys
        _warn_unused_config(state)
        # report the outcome
        exit_code = _report(
            state.conf.options.start,
            ordered_results,
            is_colored=state.conf.options.is_colored,
            verbosity=state.conf.options.verbosity,
            fail_fast=state.conf.options.fail_fast
            or any(cast("RunToxEnv", state.envs[env]).conf["fail_fast"] for env in to_run_list),
        )
        if has_previous:
            signal(SIGINT, previous)
    return exit_code


def _venv_redirect_enabled(state: State, env_dirs: dict[str, Path]) -> bool:
    redirect = venv_redirect_path(state.conf.core.get("tox_root", Path))
    at_redirect = [name for name, env_dir in env_dirs.items() if env_dir == redirect]
    if (setting := state.conf.core.get_optional("venv_redirect", bool)) is None:
        return not at_redirect  # unset: an environment living at .venv is the project's .venv
    if setting and at_redirect:
        msg = (
            f"venv_redirect is true, but tox environment {at_redirect[0]} lives at {redirect}, where the redirect file"
            " goes; set venv_redirect to false or leave it unset"
        )
        raise HandledError(msg)
    return setting


def _env_dirs(state: State) -> dict[str, Path]:
    return {name: state.envs[name].env_dir for name in state.envs.iter(only_active=False)}


class _ToxSpinner(Spinner):
    def __init__(  # keeps the signature
        self,
        enabled: bool,  # ruff:ignore[boolean-type-hint-positional-argument]  # keeps the signature
        state: State,
        total: int,  # keeps the signature
    ) -> None:
        stream = state._options.log_handler.stdout  # ruff:ignore[private-member-access]  # internal access
        super().__init__(
            # animation frames and erase sequences belong to an interactive terminal, never to redirected output
            enabled=enabled and stream.isatty(),
            colored=state.conf.options.is_colored,
            stream=stream,
            total=total,
        )

    def update_spinner(  # keeps the signature
        self,
        result: ToxEnvRunResult,
        success: bool,  # ruff:ignore[boolean-type-hint-positional-argument]  # keeps the signature
    ) -> None:
        ((self.skip if result.skipped else self.succeed) if success else self.fail)(result.name)


def _queue_and_wait(  # ruff:ignore[too-many-arguments]  # public signature
    state: State,
    to_run_list: list[str],
    results: list[ToxEnvRunResult],
    future_to_env: dict[Future[ToxEnvRunResult], ToxEnv],
    interrupt: Event,
    done: Event,
    max_workers: int | None,
    spinner: _ToxSpinner,
    live: bool,  # ruff:ignore[boolean-type-hint-positional-argument]  # keeps the signature
    error: list[BaseException],
) -> None:
    try:
        try:
            # an unbounded pool (-p all) sizes to the selection; keep at least one worker so an empty
            # selection does not raise ValueError from ThreadPoolExecutor
            workers = max(1, len(to_run_list)) if max_workers is None else max_workers
            _do_queue_and_wait(state, to_run_list, results, future_to_env, interrupt, workers, spinner, live)
        except BaseException as exception:  # ruff:ignore[blind-except] # re-raised in the main thread
            error.append(exception)
    finally:
        try:
            for name in to_run_list:
                _tear_down(state.envs[name])
        finally:
            done.set()


def _do_queue_and_wait(  # ruff:ignore[too-many-arguments]  # public signature
    state: State,
    to_run_list: list[str],
    results: list[ToxEnvRunResult],
    future_to_env: dict[Future[ToxEnvRunResult], ToxEnv],
    interrupt: Event,
    max_workers: int,
    spinner: _ToxSpinner,
    live: bool,  # ruff:ignore[boolean-type-hint-positional-argument]  # keeps the signature
) -> None:
    options = state._options  # ruff:ignore[private-member-access]  # internal access
    with spinner:
        completed: set[str] = set()
        envs_to_run_generator = _ready_to_run_envs(state, to_run_list, completed)

        def _run(tox_env: RunToxEnv) -> ToxEnvRunResult:
            spinner.add(tox_env.conf.name)
            return run_one(
                tox_env,
                options.parsed.no_test or options.parsed.package_only,
                suspend_display=live is False,
            )

        env_list: list[str] = []
        stop_scheduling = False
        fail_fast_enabled = options.parsed.fail_fast or any(
            cast("RunToxEnv", state.envs[env]).conf["fail_fast"] for env in to_run_list
        )
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="tox-driver") as executor:
            while True:
                envs_to_queue = _envs_to_queue(
                    env_list, sequential_fail_fast=max_workers == 1 and fail_fast_enabled, interrupt=interrupt
                )
                _queue_envs(
                    envs_to_queue, state, interrupt, lambda tox_env: executor.submit(_run, tox_env), future_to_env
                )
                env_list = env_list[len(envs_to_queue) :]

                if not future_to_env:
                    result: ToxEnvRunResult | None = None
                elif (completed_future := _next_completed(future_to_env, interrupt)) is None:
                    _interrupt_pending(future_to_env)
                    env_list = []
                    result = None
                else:
                    result = _collect_completed(future_to_env, completed_future, interrupt)
                    results.append(result)
                    completed.add(result.name)
                    if _stops_scheduling(result, fail_fast=options.parsed.fail_fast):
                        # stop scheduling new work but let running environments finish: only a user interrupt
                        # abandons them (cancel only stops futures the executor has not started yet)
                        stop_scheduling = True
                        env_list = []
                        _cancel_pending(future_to_env)

                if not interrupt.is_set() and not stop_scheduling and not env_list:
                    env_list = next(envs_to_run_generator, [])
                # if nothing running and nothing more to run we're done
                final_run = not env_list and not future_to_env
                if final_run:  # disable report on final env
                    spinner.print_report = False
                if result is not None:
                    _handle_one_run_done(result, spinner, state, live)
                if final_run:
                    break


def _ready_to_run_envs(state: State, to_run: list[str], completed: set[str]) -> Iterator[list[str]]:
    # Generate tox environments ready to run.
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
    """Compute the order in which the environments run, so that the environments they depend on run first.

    :param state: the state of the run
    :param to_run: the names of the environments to run

    :returns: the order of the environments, and the environments each one depends on

    :raises tox.report.HandledError: when the environments depend on each other in a cycle

    """
    to_run_set = set(to_run)
    todo: dict[str, set[str]] = {}
    for env in to_run:
        depends = set(cast("RunToxEnv", state.envs[env]).conf.get("depends", EnvList).envs)
        todo[env] = {name for dep in depends for name in to_run_set if fnmatchcase(name, dep)} - {env}
    try:
        order = stable_topological_sort(todo)
    except ValueError as exception:
        msg = f"circular dependency detected between environments: {exception}"
        raise HandledError(msg) from exception
    return order, todo


def _envs_to_queue(env_list: list[str], *, sequential_fail_fast: bool, interrupt: Event) -> list[str]:
    return env_list[:1] if sequential_fail_fast and not interrupt.is_set() else env_list


def _queue_envs(
    envs: list[str],
    state: State,
    interrupt: Event,
    submit: Callable[[RunToxEnv], Future[ToxEnvRunResult]],
    future_to_env: dict[Future[ToxEnvRunResult], ToxEnv],
) -> None:
    for env in envs:  # queue all available (or one at a time if sequential + fail-fast)
        tox_env_to_run = cast("RunToxEnv", state.envs[env])
        # queue the rest as failed upfront once interrupted
        future = _interrupted_future(tox_env_to_run, env) if interrupt.is_set() else submit(tox_env_to_run)
        future_to_env[future] = tox_env_to_run


def _interrupted_future(tox_env: RunToxEnv, name: str) -> Future[ToxEnvRunResult]:
    tox_env.teardown()
    future: Future[ToxEnvRunResult] = Future()
    future.set_result(ToxEnvRunResult(name=name, skipped=False, code=-2, outcomes=[], duration=MISS_DURATION))
    return future


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


def _interrupt_pending(future_to_env: dict[Future[ToxEnvRunResult], ToxEnv]) -> None:
    for pending_future, pending_env in list(future_to_env.items()):
        if not pending_future.cancel() and not pending_future.done():
            pending_env.interrupt()
    future_to_env.clear()


def _collect_completed(
    future_to_env: dict[Future[ToxEnvRunResult], ToxEnv],
    completed_future: Future[ToxEnvRunResult],
    interrupt: Event,
) -> ToxEnvRunResult:
    tox_env_done = future_to_env.pop(completed_future)
    try:
        return completed_future.result()
    except CancelledError:
        tox_env_done.teardown()
        was_interrupted = interrupt.is_set()
        return ToxEnvRunResult(
            name=tox_env_done.conf.name,
            skipped=not was_interrupted,
            code=-3 if was_interrupted else -2,
            outcomes=[],
            duration=MISS_DURATION,
        )


def _stops_scheduling(result: ToxEnvRunResult, *, fail_fast: bool) -> bool:
    return (
        result.code != Outcome.OK
        and not result.skipped
        and not result.ignore_outcome
        and (fail_fast or result.fail_fast)
    )


def _cancel_pending(future_to_env: dict[Future[ToxEnvRunResult], ToxEnv]) -> None:
    for pending_future in list(future_to_env.keys()):
        pending_future.cancel()


def _handle_one_run_done(
    result: ToxEnvRunResult,
    spinner: _ToxSpinner,
    state: State,
    live: bool,  # ruff:ignore[boolean-type-hint-positional-argument]  # keeps the signature
) -> None:
    success = result.code == Outcome.OK
    spinner.update_spinner(result, success)
    tox_env = cast("RunToxEnv", state.envs[result.name])
    if tox_env.journal:  # add overall journal entry
        tox_env.journal["result"] = {
            "success": success,
            "exit_code": result.code,
            "duration": result.duration,
            "skipped": result.skipped,
        }
    if live is False and state.conf.options.parallel_live is False:  # teardown background run
        out_err = tox_env.close_and_read_out_err()  # sync writes from buffer to stdout/stderr
        pkg_out_err_list = []
        for package_env in tox_env.package_envs:
            pkg_out_err = package_env.close_and_read_out_err()
            if pkg_out_err is not None:  # pragma: no branch  # other outcome untested
                pkg_out_err_list.append(pkg_out_err)
        if not success or tox_env.conf["parallel_show_output"] or state.conf.options.list_dependencies:
            for pkg_out_err in pkg_out_err_list:
                # internal access, not reached in tests
                state._options.log_handler.write_out_err(pkg_out_err)  # pragma: no cover  # ruff:ignore[private-member-access]
            if out_err is not None:  # pragma: no branch # first show package build
                state._options.log_handler.write_out_err(  # ruff:ignore[private-member-access]  # internal access
                    out_err
                )


def _tear_down(tox_env: ToxEnv) -> None:
    try:
        tox_env.teardown()
    except (Fail, OSError):  # one environment failing to clean up must not leak the others' resources
        _LOGGER.warning("failed to tear down environment %s", tox_env.conf.name, exc_info=True)


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


def _record_venv_redirect(state: State) -> None:
    env_dirs = _env_dirs(state)
    if not _venv_redirect_enabled(state, env_dirs) or (target := _venv_redirect_target(state, env_dirs)) is None:
        return
    core = state.conf.core
    work_dir, ours = core.get("work_dir", Path), set(env_dirs.values())
    record_venv_redirect(core.get("tox_root", Path), target, lambda path: path in ours or path.is_relative_to(work_dir))


def _venv_redirect_target(state: State, env_dirs: dict[str, Path]) -> Path | None:
    # the pick depends on the configuration alone, so it stays the same whichever environments ran
    if (pinned := state.conf.core.get_optional("venv_redirect_env", str)) is not None and pinned not in env_dirs:
        _LOGGER.warning("venv_redirect_env names %s, which is not a tox environment", pinned)
        return None
    develop = next((name for name in env_dirs if _installs_develop(state.envs[name])), None)
    name = pinned or ("dev" if "dev" in env_dirs else develop)
    return env_dirs[name] if name is not None and (env_dirs[name] / "pyvenv.cfg").exists() else None


def _installs_develop(env: ToxEnv) -> bool:
    return "package" in env.conf and env.conf["package"] in {"editable", "editable-legacy"}


def _warn_unused_config(state: State) -> None:
    if state.conf.options.verbosity <= DEFAULT_VERBOSITY:
        return
    is_colored = state.conf.options.is_colored
    for name in state.envs.iter():
        if unused := state.envs[name].conf.unused():
            _print_unused(is_colored, f"[testenv:{name}]", unused)
    if unused := state.conf.core.unused():
        _print_unused(is_colored, "[tox]", unused)


def _print_unused(  # keeps the signature
    is_colored: bool,  # ruff:ignore[boolean-type-hint-positional-argument]  # keeps the signature
    section: str,
    unused: list[str],  # keeps the signature
) -> None:
    msg = f"  {section} unused config key(s): {', '.join(unused)}"
    print(  # ruff:ignore[print]  # terminal output
        f"{Fore.YELLOW if is_colored else ''}{msg}{Fore.RESET if is_colored else ''}"
    )


def _report(
    start: float,
    runs: list[ToxEnvRunResult],
    *,
    is_colored: bool,
    verbosity: int,
    fail_fast: bool,
) -> int:
    def _print(color_: str, message: str) -> None:
        if verbosity:
            print(  # ruff:ignore[print]  # terminal output
                f"{color_ if is_colored else ''}{message}{Fore.RESET if is_colored else ''}"
            )

    successful, skipped = [], []
    for run in runs:
        successful.append(run.code == Outcome.OK or run.ignore_outcome or run.unavailable)
        skipped.append(run.skipped)
        # durations are shown from verbosity 2
        duration_individual = [o.elapsed for o in run.outcomes] if verbosity >= 2 else []  # ruff:ignore[magic-value-comparison]
        extra = f"+cmd[{','.join(f'{i:.2f}' for i in duration_individual)}]" if duration_individual else ""
        setup = run.duration - sum(duration_individual)
        msg, color = _get_outcome_message(run)
        out = f"  {run.name}: {msg} ({run.duration:.2f}{f'=setup[{setup:.2f}]{extra}' if extra else ''} seconds)"
        _print(color, out)

    duration = time.monotonic() - start
    if all(successful) and not all(skipped):
        _print(Fore.GREEN, f"  congratulations :) ({duration:.2f} seconds)")
        return Outcome.OK
    _print(Fore.RED, f"  evaluation failed :( ({duration:.2f} seconds)")
    if len(runs) == 1:
        return runs[0].code if not runs[0].skipped else 1
    if fail_fast:
        # under fail fast the run stops at the first failure, whose code is the documented overall exit code
        first_failed = next(
            (r for r in runs if not r.skipped and not r.ignore_outcome and not r.unavailable and r.code != Outcome.OK),
            None,
        )
        if first_failed is not None:
            return first_failed.code
    return 1


def _get_outcome_message(run: ToxEnvRunResult) -> tuple[str, str]:
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


__all__ = [
    "InstallPackageAction",
    "SkipMissingInterpreterAction",
    "env_run_create_flags",
    "execute",
    "run_order",
]
