"""
Execute a command in a tox environment.
"""
from pathlib import Path
from typing import Optional

from tox.config.cli.parser import ToxParser
from tox.config.loader.memory import MemoryLoader
from tox.config.types import Command
from tox.plugin import impl
from tox.report import HandledError
from tox.session.cmd.run.common import env_run_create_flags
from tox.session.cmd.run.sequential import run_sequential
from tox.session.common import CliEnv, env_list_flag
from tox.session.state import State


@impl
def tox_add_option(parser: ToxParser) -> None:
    our = parser.add_command("exec", ["e"], "execute an arbitrary command within a tox environment", exec_)
    our.epilog = "For example: tox exec -e py39 -- python --version"
    env_list_flag(our, default=CliEnv("py"), multiple=False)
    env_run_create_flags(our, mode="exec")


def exec_(state: State) -> int:
    env_list = list(state.env_list(everything=False))
    if len(env_list) != 1:
        raise HandledError(f"exactly one target environment allowed in exec mode but found {', '.join(env_list)}")
    loader = MemoryLoader(  # these configuration values are loaded from in-memory always (no file conf)
        commands_pre=[],
        commands=[],
        commands_post=[],
    )
    conf = state.conf.get_env(env_list[0], loaders=[loader])
    to_path: Optional[Path] = conf["change_dir"] if conf["args_are_paths"] else None
    pos_args = state.conf.pos_args(to_path)
    if not pos_args:
        raise HandledError("You must specify a command as positional arguments, use -- <command>")
    loader.raw["commands"] = [Command(list(pos_args))]
    return run_sequential(state)
