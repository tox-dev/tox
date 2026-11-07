"""Main entry point for tox."""

from __future__ import annotations

import faulthandler
import logging
import os
import sys
import time
from typing import TYPE_CHECKING

from .config.cli.parse import get_options
from .report import HandledError, ToxHandler
from .session.state import State

if TYPE_CHECKING:
    from collections.abc import Sequence


__all__ = [
    "run",
]


def run(args: Sequence[str] | None = None) -> None:
    try:
        with ToxHandler.patch_thread():
            result = main(sys.argv[1:] if args is None else args)
    except Exception as exception:
        if isinstance(exception, HandledError):
            logging.error(  # ruff:ignore[error-instead-of-exception]  # expected error log
                "%s| %s", type(exception).__name__, exception
            )
            result = -2
        else:
            raise
    except KeyboardInterrupt:
        result = -2
    finally:
        if "_TOX_SHOW_THREAD" in os.environ:  # pragma: no cover  # setup not built by tests
            import threading  # pragma: no cover  # ruff:ignore[import-outside-top-level]  # avoids an import cycle

            for thread in threading.enumerate():  # pragma: no cover  # setup not built by tests
                print(thread)  # pragma: no cover  # ruff:ignore[print]  # terminal output
    raise SystemExit(result)


def main(args: Sequence[str]) -> int:
    state = setup_state(args)
    from .provision import provision  # ruff:ignore[import-outside-top-level]  # avoids an import cycle

    if (result := provision(state)) is not False:
        return result
    # internal access
    handler = state._options.cmd_handlers[state.conf.options.command]  # ruff:ignore[private-member-access]
    return handler(state)


def setup_state(args: Sequence[str]) -> State:
    """Setup the state object of this run.

    :param args: the command line arguments

    :returns: the state of this run

    """
    start = time.monotonic()
    # parse CLI arguments
    options = get_options(*args)
    options.parsed.start = start
    if options.parsed.exit_and_dump_after:
        # debug option that ends the process, not reached in tests
        faulthandler.dump_traceback_later(timeout=options.parsed.exit_and_dump_after, exit=True)  # pragma: no cover
    # build tox environment config objects
    return State(options, args)
