"""Main entry point for tox."""
import logging
import sys
import time
from itertools import chain
from pathlib import Path
from typing import Optional, Sequence

from tox.config.cli.parse import get_options
from tox.config.cli.parser import Parsed
from tox.config.main import Config
from tox.config.source.tox_ini import ToxIni
from tox.provision import provision
from tox.report import HandledError, ToxHandler
from tox.session.state import State


def run(args: Optional[Sequence[str]] = None) -> None:
    try:
        with ToxHandler.patch_thread():
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
    handler = state.cmd_handlers[command]
    result = handler(state)
    return result


def setup_state(args: Sequence[str]) -> State:
    """Setup the state object of this run."""
    start = time.monotonic()
    # parse CLI arguments
    parsed, handlers, pos_args, log_handler = get_options(*args)
    parsed.start = start
    # parse configuration file
    config = make_config(parsed, pos_args)
    # build tox environment config objects
    state = State(config, (parsed, handlers), args, log_handler)
    return state


def make_config(parsed: Parsed, pos_args: Optional[Sequence[str]]) -> Config:
    """Make a tox configuration object."""
    # for now only tox.ini supported, assume empty tox.ini where pyproject.toml or in cwd
    tox_ini: Optional[Path] = parsed.config_file
    work_dir: Optional[Path] = parsed.work_dir
    if work_dir is not None:
        work_dir = work_dir.absolute()
    if tox_ini is None:
        folder = Path.cwd() if work_dir is None else work_dir
        candidate_names = "tox.ini", "pyproject.toml"
        for name in candidate_names:
            for base in chain([folder], folder.parents):
                candidate: Path = base / name
                if candidate.exists() and candidate.is_file():
                    tox_ini = candidate
                    break
            if tox_ini is not None:
                break
        if tox_ini is None:
            tox_ini = folder / "tox.ini"
            logging.warning(f"No {' or '.join(candidate_names)} found, assuming empty tox.ini at {tox_ini}")
        if work_dir is None:
            work_dir = tox_ini.parent
    else:
        tox_ini = tox_ini.absolute()
        work_dir = tox_ini.parent if work_dir is None else work_dir

    ini_loader = ToxIni(tox_ini)
    return Config(
        config_source=ini_loader,
        overrides=parsed.override,
        pos_args=pos_args,
        root=parsed.root_dir if parsed.root_dir is not None else tox_ini.parent,
        work_dir=work_dir,
    )
