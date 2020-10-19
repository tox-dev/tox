"""Main entry point for tox."""
import sys
from pathlib import Path
from typing import Optional, Sequence

from tox.config.cli.parse import get_options
from tox.config.main import Config
from tox.config.source.ini import Ini
from tox.session.state import State
from tox.tox_env.builder import build_tox_envs


def run(args: Optional[Sequence[str]] = None) -> None:
    try:
        result = main(sys.argv[1:] if args is None else args)
    except KeyboardInterrupt:
        result = -2
    raise SystemExit(result)


def main(args: Sequence[str]) -> int:
    state = setup_state(args)
    command = state.options.command
    handler = state.handlers[command]
    result = handler(state)
    if result is None:
        result = 0
    return result


def setup_state(args: Sequence[str]) -> State:
    """Setup the state object of this run."""
    # parse CLI arguments
    options = get_options(*args)
    # parse configuration file
    config = make_config(Path().absolute())
    # build tox environment config objects
    state = build_tox_envs(config, options, args)
    return state


def make_config(path: Path) -> Config:
    """Make a tox configuration object."""
    # for now only tox.ini supported
    ini_loader = Ini(path / "tox.ini")
    return Config(ini_loader)
