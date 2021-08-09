"""
Defines how to run a single tox environment.
"""
import logging
import time
from pathlib import Path
from typing import List, NamedTuple, Tuple

from tox.config.types import Command
from tox.execute.api import Outcome, StdinSource
from tox.tox_env.errors import Fail, Skip
from tox.tox_env.python.virtual_env.package.api import ToxBackendFailed
from tox.tox_env.runner import RunToxEnv

LOGGER = logging.getLogger(__name__)


class ToxEnvRunResult(NamedTuple):
    name: str
    skipped: bool
    code: int
    outcomes: List[Outcome]
    duration: float
    ignore_outcome: bool = False


def run_one(tox_env: RunToxEnv, no_test: bool, suspend_display: bool) -> ToxEnvRunResult:
    start_one = time.monotonic()
    name = tox_env.conf.name
    with tox_env.display_context(suspend_display):
        skipped, code, outcomes = _evaluate(tox_env, no_test)
    duration = time.monotonic() - start_one
    return ToxEnvRunResult(name, skipped, code, outcomes, duration, tox_env.conf["ignore_outcome"])


def _evaluate(tox_env: RunToxEnv, no_test: bool) -> Tuple[bool, int, List[Outcome]]:
    skipped = False
    code: int = 0
    outcomes: List[Outcome] = []
    try:
        try:
            tox_env.setup()
            code, outcomes = run_commands(tox_env, no_test)
        except Skip as exception:
            LOGGER.warning("skipped because %s", exception)
            skipped = True
        except ToxBackendFailed as exception:
            LOGGER.error("%s", exception)
            raise SystemExit(exception.code)
        except Fail as exception:
            LOGGER.error("failed with %s", exception)
            code = 1
        except Exception:  # noqa # pragma: no cover
            LOGGER.exception("internal error")  # pragma: no cover
            code = 2  # pragma: no cover
        finally:
            tox_env.teardown()
    except SystemExit as exception:  # setup command fails (interrupted or via invocation)
        code = exception.code
    return skipped, code, outcomes


def run_commands(tox_env: RunToxEnv, no_test: bool) -> Tuple[int, List[Outcome]]:
    outcomes: List[Outcome] = []
    if no_test:
        status_pre, status_main, status_post = Outcome.OK, Outcome.OK, Outcome.OK
    else:
        chdir: Path = tox_env.conf["change_dir"]
        ignore_errors: bool = tox_env.conf["ignore_errors"]
        try:
            status_pre = run_command_set(tox_env, "commands_pre", chdir, ignore_errors, outcomes)
            if status_pre == Outcome.OK or ignore_errors:
                status_main = run_command_set(tox_env, "commands", chdir, ignore_errors, outcomes)
            else:
                status_main = Outcome.OK
        finally:
            status_post = run_command_set(tox_env, "commands_post", chdir, ignore_errors, outcomes)
    exit_code = status_pre or status_main or status_post  # first non-success
    return exit_code, outcomes


def run_command_set(tox_env: RunToxEnv, key: str, cwd: Path, ignore_errors: bool, outcomes: List[Outcome]) -> int:
    exit_code = Outcome.OK
    command_set: List[Command] = tox_env.conf[key]
    for at, cmd in enumerate(command_set):
        current_outcome = tox_env.execute(
            cmd.args,
            cwd=cwd,
            stdin=StdinSource.user_only(),
            show=True,
            run_id=f"{key}[{at}]",
        )
        outcomes.append(current_outcome)
        try:
            current_outcome.assert_success()
        except SystemExit as exception:
            if cmd.ignore_exit_code:
                continue
            if ignore_errors:
                if exit_code == Outcome.OK:
                    exit_code = exception.code  # ignore errors continues ahead but saves the exit code
                continue
            return exception.code
    return exit_code


__all__ = (
    "run_one",
    "ToxEnvRunResult",
)
