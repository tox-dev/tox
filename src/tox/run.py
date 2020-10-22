"""Main entry point for tox."""
import logging
import sys
from pathlib import Path
from typing import List, Optional, Sequence, cast

from tox.config.cli.parse import get_options
from tox.config.main import Config
from tox.config.override import Override
from tox.config.source.ini import ToxIni
from tox.session.state import State
from tox.tox_env.builder import build_tox_envs


def run(args: Optional[Sequence[str]] = None) -> None:
    try:
        result = main(sys.argv[1:] if args is None else args)
    except Exception as exception:
        logging.error("%s| %s", type(exception).__name__, str(exception))
        result = -2
    except KeyboardInterrupt:
        result = -2
    raise SystemExit(result)


def main(args: Sequence[str]) -> int:
    state = setup_state(args)
    command = state.options.command
    handler = state.handlers[command]
    result = cast(int, handler(state))
    if result is None:
        result = 0
    return result


def setup_state(args: Sequence[str]) -> State:
    """Setup the state object of this run."""
    # parse CLI arguments
    options = get_options(*args)
    # parse configuration file
    config = make_config(Path().cwd().absolute(), options[0].override)
    # build tox environment config objects
    state = build_tox_envs(config, options, args)
    return state


def make_config(path: Path, overrides: List[Override]) -> Config:
    """Make a tox configuration object."""
    # for now only tox.ini supported
    folder = path
    while True:
        tox_ini = folder / "tox.ini"
        if tox_ini.exists() and tox_ini.is_file():
            ini_loader = ToxIni(tox_ini)
            return Config(ini_loader, overrides)
        if folder.parent == folder:
            break
        folder = folder.parent
    raise RuntimeError(f"could not find tox.ini in folder (or any of its parents) {path}")
