from __future__ import annotations

import locale
import logging
import os
import signal
import sys
from io import TextIOWrapper
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Final, cast

from tox.execute.local_sub_process import LocalSubProcessExecutor
from tox.execute.request import ExecuteRequest, StdinSource
from tox.report import NamedBytesIO

if TYPE_CHECKING:
    from types import FrameType

    from tox.execute import Outcome
    from tox.execute.api import ExecuteStatus
    from tox.tox_env.api import ToxEnv

logging.basicConfig(level=logging.DEBUG, format="%(relativeCreated)d\t%(levelname).1s\t%(message)s")
bad_process: Final[Path] = Path(__file__).parent / "bad_process.py"

executor: Final[LocalSubProcessExecutor] = LocalSubProcessExecutor(colored=False)
request = ExecuteRequest(
    cmd=[sys.executable, bad_process, sys.argv[1]],
    cwd=Path().absolute(),
    env=os.environ.copy(),
    stdin=StdinSource.API,
    run_id="",
)
out_err = (
    TextIOWrapper(NamedBytesIO("out"), encoding=locale.getpreferredencoding(False)),
    TextIOWrapper(NamedBytesIO("err"), encoding=locale.getpreferredencoding(False)),
)


def show_outcome(outcome: Outcome | None) -> None:
    if outcome is not None:  # pragma: no branch  # other outcome untested
        print(outcome.exit_code)  # ruff:ignore[print]  # test output
        print(repr(outcome.out))  # ruff:ignore[print]  # test output
        print(repr(outcome.err))  # ruff:ignore[print]  # test output
        print(outcome.elapsed, end="")  # ruff:ignore[print]  # test output
        print("done show outcome", file=sys.stderr)  # ruff:ignore[print]  # test output


def handler(signum: int, frame: FrameType | None) -> None:
    logging.info("signal %s at %s", signum, frame)
    global _INTERRUPT_DONE  # ruff:ignore[global-statement]  # signal handler flag
    if _INTERRUPT_DONE is False:  # pragma: no branch  # other outcome untested
        _INTERRUPT_DONE = True
        logging.info("interrupt via %s", status)
        status.interrupt()
        logging.info("interrupt finished via %s", status)


def _wait_for_exit(status: ExecuteStatus) -> None:
    logging.info("wait on %r", status)
    while status.exit_code is None:
        status.wait(timeout=0.01)  # use wait here with timeout to not block the main thread
    logging.info("wait over on %r", status)


_INTERRUPT_DONE = False
signal.signal(signal.SIGINT, handler)
logging.info("PID %d start %r", os.getpid(), request)
tox_env: Final[ToxEnv] = cast(
    "ToxEnv",
    SimpleNamespace(
        conf={"suicide_timeout": 0.01, "interrupt_timeout": 0.05, "terminate_timeout": 0.07},
        options=SimpleNamespace(no_capture=False),
    ),
)

_STATUS_OUTCOME: Outcome | None = None
try:
    with executor.call(request, show=False, out_err=out_err, env=tox_env) as status:
        _wait_for_exit(status)
    _STATUS_OUTCOME = status.outcome
except Exception as exception:  # pragma: no cover  # untested error path
    logging.exception(exception)  # ruff:ignore[verbose-log-message] # pragma: no cover  # untested error path
finally:
    logging.info("done")
    logging.shutdown()
show_outcome(_STATUS_OUTCOME)
