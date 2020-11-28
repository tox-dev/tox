from pathlib import Path

from tox.config.cli.parser import ToxParser
from tox.config.loader.memory import MemoryLoader
from tox.plugin.impl import impl
from tox.report import HandledError
from tox.session.cmd.run.common import env_run_create_flags
from tox.session.cmd.run.sequential import run_sequential
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
    env_list = list(state.env_list(everything=False))
    if len(env_list) != 1:
        raise HandledError(f"exactly one target environment allowed in devenv mode but found {', '.join(env_list)}")
    loader = MemoryLoader(  # these configuration values are loaded from in-memory always (no file conf)
        # dev environments must be of type dev
        usedevelop=True,
        # move it in source
        env_dir=Path(state.options.devenv_path),
    )

    state.options.no_test = True  # do not run the test phase
    state.conf.get_env(env_list[0], loaders=[loader])
    return run_sequential(state)
