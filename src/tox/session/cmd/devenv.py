from pathlib import Path

from tox.config.cli.parser import ToxParser
from tox.config.loader.memory import MemoryLoader
from tox.plugin.impl import impl
from tox.session.cmd.run.common import env_run_create_flags
from tox.session.cmd.run.single import run_one
from tox.session.common import CliEnv, env_list_flag
from tox.session.state import State


@impl
def tox_add_option(parser: ToxParser) -> None:
    our = parser.add_command(
        "devenv",
        ["d"],
        "sets up a development environment at ENVDIR based on the env's tox configuration specified ",
        devenv,
    )
    our.add_argument("devenv_path", metavar="path", default=Path("venv").absolute(), nargs="?")
    env_list_flag(our, default=CliEnv("py"))
    env_run_create_flags(our)


def devenv(state: State) -> int:
    loader = MemoryLoader(  # these configuration values are loaded from in-memory always (no file conf)
        # dev environments must be of type dev
        usedevelop=True,
        # move it in source
        env_dir=state.options.devenv_path,
    )
    env = state.options.env[0]
    state.conf.get_env(env, loaders=[loader])

    tox_env = state.tox_env(name=env)
    return run_one(tox_env, state.options.recreate, True)
