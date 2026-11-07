"""Defines how to run a single tox environment."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Final, NamedTuple, cast

from tox.config.types import Command
from tox.execute.api import Outcome, StdinSource
from tox.report import HandledError
from tox.tox_env.errors import Fail, Skip
from tox.tox_env.python.virtual_env.package.pyproject import ToxBackendFailed

if TYPE_CHECKING:
    from collections.abc import Callable

    from tox.tox_env.api import ToxEnv
    from tox.tox_env.runner import RunToxEnv

LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


def run_one(  # keeps the signature
    tox_env: RunToxEnv,
    no_test: bool,  # ruff:ignore[boolean-type-hint-positional-argument]  # keeps the signature
    suspend_display: bool,  # ruff:ignore[boolean-type-hint-positional-argument]  # keeps the signature
) -> ToxEnvRunResult:
    """Run a single environment, and report its result.

    :param tox_env: the environment to run
    :param no_test: whether to only set up the environment, without running its commands
    :param suspend_display: whether to suspend the display of the environment while it runs

    :returns: the result of the run
    """
    start_one = time.monotonic()
    name = tox_env.conf.name
    with tox_env.display_context(suspend_display):
        try:
            skipped, code, outcomes = _run_with_teardown(tox_env, no_test)
        except SystemExit as exception:  # setup command fails (interrupted or via invocation)
            skipped, code, outcomes = False, cast("int", exception.code), []
    duration = time.monotonic() - start_one
    return ToxEnvRunResult(
        name, skipped, code, outcomes, duration, tox_env.conf["ignore_outcome"], tox_env.conf["fail_fast"]
    )


def _run_with_teardown(  # keeps the signature
    tox_env: RunToxEnv,
    no_test: bool,  # ruff:ignore[boolean-type-hint-positional-argument]  # keeps the signature
) -> _Evaluation:
    skipped = False
    code: int = 0
    outcomes: list[Outcome] = []
    try:
        tox_env.setup()
        code, outcomes = run_commands(tox_env, no_test)
    except Skip as exception:
        LOGGER.warning("skipped because %s", exception)
        code = 0
        skipped = True
    except ToxBackendFailed as exception:
        LOGGER.error("%s", exception)  # ruff:ignore[error-instead-of-exception]  # expected error log
        raise SystemExit(exception.code)  # ruff:ignore[raise-without-from-inside-except]  # original error not chained
    except Fail as exception:
        LOGGER.error("failed with %s", exception)  # ruff:ignore[error-instead-of-exception]  # expected error log
        code = 1
    except HandledError as exception:
        LOGGER.error("%s", exception)  # ruff:ignore[error-instead-of-exception]  # expected error log
        code = 1
    except Exception:  # pragma: no cover  # untested error path
        LOGGER.exception("internal error")  # pragma: no cover  # untested error path
        code = 2  # pragma: no cover  # untested error path
    finally:
        tox_env.teardown()
    return _Evaluation(skipped, code, outcomes)


def run_commands(  # keeps the signature
    tox_env: RunToxEnv,
    no_test: bool,  # ruff:ignore[boolean-type-hint-positional-argument]  # keeps the signature
) -> tuple[int, list[Outcome]]:
    outcomes: list[Outcome] = []
    if no_test:
        exit_code = Outcome.OK
    else:
        # importing this here to avoid circular import
        from tox.plugin.manager import MANAGER  # ruff:ignore[import-outside-top-level]

        chdir = tox_env.conf.get("change_dir", Path)
        chdir.mkdir(exist_ok=True, parents=True)
        ignore_errors = tox_env.conf.get("ignore_errors", bool)
        retry_count = tox_env.conf.get("commands_retry", int)
        interrupt_post_commands = tox_env.conf.get("interrupt_post_commands", bool)
        MANAGER.tox_before_run_commands(tox_env)
        status_pre, status_main, status_post = -1, -1, -1
        try:
            status_pre = run_command_set(tox_env, "commands_pre", chdir, ignore_errors, outcomes, retry_count)
            if status_pre == Outcome.OK or ignore_errors:
                status_main = run_command_set(tox_env, "commands", chdir, ignore_errors, outcomes, retry_count)
            else:
                status_main = Outcome.OK
        finally:
            with tox_env.allow_post_commands_after_interrupt(interrupt_post_commands):
                status_post = run_command_set(tox_env, "commands_post", chdir, ignore_errors, outcomes, retry_count)
            exit_code = status_pre or status_main or status_post  # first non-success
            MANAGER.tox_after_run_commands(tox_env, exit_code, outcomes)
    return exit_code, outcomes


def run_command_set(  # ruff:ignore[too-many-arguments]  # public signature
    tox_env: ToxEnv,
    key: str,
    cwd: Path,
    ignore_errors: bool,  # ruff:ignore[boolean-type-hint-positional-argument]  # keeps the signature
    outcomes: list[Outcome],
    retry_count: int = 0,
) -> int:
    """Run a set of commands of an environment, retrying them when they fail.

    :param tox_env: the environment the commands run in
    :param key: the configuration key of the commands
    :param cwd: the directory the commands run in
    :param ignore_errors: whether a failing command does not fail the run
    :param outcomes: the list the outcome of each command is added to
    :param retry_count: how many times the commands are retried when they fail

    :returns: the exit code
    """

    def _execute(cmd: Command, run_id: str) -> Outcome:
        return tox_env.execute(
            cmd.args,
            cwd=cwd,
            stdin=StdinSource.USER if getattr(tox_env.options, "no_capture", False) else StdinSource.user_only(),
            show=True,
            run_id=run_id,
        )

    exit_code = Outcome.OK
    for at, cmd in enumerate(tox_env.conf.get(key, list[Command])):
        max_attempts = 1 if cmd.ignore_exit_code else retry_count + 1
        failed_code = _run_attempts(cmd, f"{key}[{at}]", max_attempts, outcomes, _execute)
        if failed_code is None:
            continue
        if not ignore_errors:
            return failed_code
        if exit_code == Outcome.OK:
            exit_code = failed_code
    return exit_code


def _run_attempts(
    cmd: Command,
    run_id: str,
    max_attempts: int,
    outcomes: list[Outcome],
    execute: Callable[[Command, str], Outcome],
) -> int | None:
    for attempt in range(1, max_attempts + 1):
        current_outcome = execute(cmd, run_id)
        outcomes.append(current_outcome)
        try:
            if cmd.invert_exit_code:
                current_outcome.assert_failure()
            else:
                current_outcome.assert_success()
        except SystemExit as exception:
            if cmd.ignore_exit_code:
                logging.warning("command failed but is marked ignore outcome so handling it as success")
                return None
            if attempt < max_attempts:
                logging.warning(
                    "command failed (attempt %d of %d), retrying ...: %s",
                    attempt,
                    max_attempts,
                    current_outcome.request.shell_cmd_redacted,
                )
                continue
            return cast("int", exception.code)
        else:
            return None
    return None


class _Evaluation(NamedTuple):
    skipped: bool
    code: int
    outcomes: list[Outcome]


class ToxEnvRunResult(NamedTuple):
    """The result of running an environment.

    :param name: the name of the environment
    :param skipped: whether the environment was skipped
    :param code: the exit code of the run
    :param outcomes: the outcome of each command that ran
    :param duration: the seconds the run took
    :param ignore_outcome: whether a failure of the environment is ignored
    :param fail_fast: whether the run stops when the environment fails
    :param unavailable: whether the environment is unavailable
    """

    name: str
    skipped: bool
    code: int
    outcomes: list[Outcome]
    duration: float
    ignore_outcome: bool = False
    fail_fast: bool = False
    unavailable: bool = False


__all__ = [
    "ToxEnvRunResult",
    "run_command_set",
    "run_one",
]
