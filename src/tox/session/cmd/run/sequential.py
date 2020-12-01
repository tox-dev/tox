"""
Run tox environments in sequential order.
"""
from typing import Iterator

from tox.config.cli.parser import ToxParser
from tox.plugin.impl import impl
from tox.session.common import env_list_flag
from tox.session.state import State

from .common import env_run_create_flags, run_and_report
from .single import ToxEnvRunResult, run_one


@impl
def tox_add_option(parser: ToxParser) -> None:
    our = parser.add_command("run", ["r"], "run environments", run_sequential)
    env_list_flag(our)
    env_run_create_flags(our)


def run_sequential(state: State) -> int:
    return run_and_report(state, _execute_sequential(state))


def _execute_sequential(state: State) -> Iterator[ToxEnvRunResult]:
    for name in state.env_list(everything=False):
        yield run_one(
            tox_env=state.tox_env(name),
            recreate=state.options.recreate,
            no_test=state.options.no_test,
            suspend_display=False,
        )
