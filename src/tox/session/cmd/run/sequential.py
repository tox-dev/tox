"""
Run tox environments in sequential order.
"""
from __future__ import annotations

from tox.config.cli.parser import ToxParser
from tox.plugin import impl
from tox.session.common import env_list_flag
from tox.session.state import State

from .common import env_run_create_flags, execute


@impl
def tox_add_option(parser: ToxParser) -> None:
    our = parser.add_command("run", ["r"], "run environments", run_sequential)
    env_list_flag(our)
    env_run_create_flags(our, mode="run")


def run_sequential(state: State) -> int:
    return execute(state, max_workers=1, has_spinner=False, live=True)
