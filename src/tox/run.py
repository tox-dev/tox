"""Main entry point for tox."""
import logging
import sys
from datetime import datetime
from typing import Optional, Sequence

from tox.config.cli.parse import get_options
from tox.config.cli.parser import Parsed
from tox.config.main import Config
from tox.config.source.tox_ini import ToxIni
from tox.provision import provision
from tox.report import HandledError
from tox.session.state import State


def run(args: Optional[Sequence[str]] = None) -> None:
    try:
        result = main(sys.argv[1:] if args is None else args)
    except Exception as exception:
        if isinstance(exception, HandledError):
            logging.error("%s| %s", type(exception).__name__, str(exception))
            result = -2
        else:
            raise
    except KeyboardInterrupt:
        result = -2
    raise SystemExit(result)


def main(args: Sequence[str]) -> int:
    state = setup_state(args)
    result = provision(state)
    if result is not False:
        return result
    command = state.options.command
    handler = state.handlers[command]
    result = handler(state)
    return result


def setup_state(args: Sequence[str]) -> State:
    """Setup the state object of this run."""
    start = datetime.now()
    # parse CLI arguments
    parsed, handlers, pos_args = get_options(*args)
    parsed.start = start
    # parse configuration file
    config = make_config(parsed, pos_args)
    # build tox environment config objects
    state = State(config, (parsed, handlers), args)
    return state


def make_config(parsed: Parsed, pos_args: Optional[Sequence[str]]) -> Config:
    """Make a tox configuration object."""
    # for now only tox.ini supported
    folder = parsed.work_dir
    while True:
        tox_ini = folder / "tox.ini"
        if tox_ini.exists() and tox_ini.is_file():
            ini_loader = ToxIni(tox_ini)
            return Config(ini_loader, parsed.override, tox_ini.parent, pos_args, parsed.work_dir)
        if folder.parent == folder:
            break
        folder = folder.parent
    raise RuntimeError(f"could not find tox.ini in folder (or any of its parents) {parsed.work_dir}")
