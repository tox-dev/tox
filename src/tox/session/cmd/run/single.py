"""
Defines how to run a single tox environment.
"""
import logging
import time
from typing import List, NamedTuple, Tuple, cast

from tox.config.types import Command
from tox.execute.api import Outcome, StdinSource
from tox.tox_env.api import ToxEnv
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


def run_one(tox_env: RunToxEnv, recreate: bool, no_test: bool, suspend_display: bool) -> ToxEnvRunResult:
    start_one = time.monotonic()
    name = tox_env.conf.name
    with tox_env.display_context(suspend_display):
        skipped, code, outcomes = _evaluate(tox_env, recreate, no_test)
    duration = time.monotonic() - start_one
    return ToxEnvRunResult(name, skipped, code, outcomes, duration)


def _evaluate(tox_env: ToxEnv, recreate: bool, no_test: bool) -> Tuple[bool, int, List[Outcome]]:
    skipped = False
    code: int = 0
    outcomes: List[Outcome] = []
    try:
        try:
            tox_env.ensure_setup(recreate=recreate)
            code, outcomes = run_commands(tox_env, no_test)
        except Skip as exception:
            LOGGER.info("skipped environment because %s", exception)
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


def run_commands(tox_env: ToxEnv, no_test: bool) -> Tuple[int, List[Outcome]]:
    status = Outcome.OK  # assume all good
    outcomes: List[Outcome] = []
    if no_test is False:
        keys = ("commands_pre", "commands", "commands_post")
        for key in keys:
            for at, cmd in enumerate(cast(List[Command], tox_env.conf[key])):
                current_outcome = tox_env.execute(
                    cmd.args,
                    cwd=tox_env.conf["change_dir"],
                    stdin=StdinSource.user_only(),
                    show=True,
                    run_id=f"{key}[{at}]",
                )
                outcomes.append(current_outcome)
                if cmd.ignore_exit_code:
                    continue
                try:
                    current_outcome.assert_success()
                except SystemExit as exception:
                    return exception.code, outcomes
    return status, outcomes


__all__ = (
    "run_one",
    "ToxEnvRunResult",
)
