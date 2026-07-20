"""Main entry point for tox."""

from __future__ import annotations

import faulthandler
import logging
import os
import sys
import time
from typing import TYPE_CHECKING

from tox.config.cli.parse import get_options
from tox.report import HandledError, ToxHandler
from tox.session.state import State

if TYPE_CHECKING:
    from collections.abc import Sequence


def run(args: Sequence[str] | None = None) -> None:
    try:
        with ToxHandler.patch_thread():
            result = main(sys.argv[1:] if args is None else args)
    except Exception as exception:
        if isinstance(exception, HandledError):
            logging.error("%s| %s", type(exception).__name__, exception)  # ruff:ignore[error-instead-of-exception]
            result = -2
        else:
            raise
    except KeyboardInterrupt:
        result = -2
    finally:
        if "_TOX_SHOW_THREAD" in os.environ:  # pragma: no cover
            import threading  # pragma: no cover  # ruff:ignore[import-outside-top-level]

            for thread in threading.enumerate():  # pragma: no cover
                print(thread)  # pragma: no cover  # ruff:ignore[print]
    raise SystemExit(result)


def main(args: Sequence[str]) -> int:
    state = setup_state(args)
    from tox.provision import provision  # ruff:ignore[import-outside-top-level]

    result = provision(state)
    if result is not False:
        return result
    handler = state._options.cmd_handlers[state.conf.options.command]  # ruff:ignore[private-member-access]
    return handler(state)


def setup_state(args: Sequence[str]) -> State:
    """Setup the state object of this run."""
    start = time.monotonic()
    # parse CLI arguments
    options = get_options(*args)
    options.parsed.start = start
    if options.parsed.exit_and_dump_after:
        faulthandler.dump_traceback_later(timeout=options.parsed.exit_and_dump_after, exit=True)  # pragma: no cover
    # build tox environment config objects
    return State(options, args)
