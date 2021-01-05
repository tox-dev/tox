import logging
import os
import signal
import sys
from io import TextIOWrapper
from pathlib import Path
from types import FrameType
from typing import Optional

from tox.execute import Outcome
from tox.execute.local_sub_process import LocalSubProcessExecutor
from tox.execute.request import ExecuteRequest, StdinSource
from tox.report import NamedBytesIO

logging.basicConfig(level=logging.DEBUG, format="%(relativeCreated)d\t%(levelname).1s\t%(message)s")
bad_process = Path(__file__).parent / "bad_process.py"

executor = LocalSubProcessExecutor(colored=False)
request = ExecuteRequest(
    cmd=[sys.executable, bad_process, sys.argv[1]],
    cwd=Path().absolute(),
    env=os.environ.copy(),
    stdin=StdinSource.API,
    run_id="",
)
out_err = TextIOWrapper(NamedBytesIO("out")), TextIOWrapper(NamedBytesIO("err"))


def show_outcome(outcome: Optional[Outcome]) -> None:
    if outcome is not None:  # pragma: no branch
        print(outcome.exit_code)
        print(repr(outcome.out))
        print(repr(outcome.err))
        print(outcome.elapsed, end="")
        print("done show outcome", file=sys.stderr)


def handler(s: signal.Signals, f: FrameType) -> None:
    logging.info(f"signal {s} at {f}")
    global interrupt_done
    if interrupt_done is False:  # pragma: no branch
        interrupt_done = True
        logging.info(f"interrupt via {status}")
        status.interrupt()
        logging.info(f"interrupt finished via {status}")


interrupt_done = False
signal.signal(signal.SIGINT, handler)
logging.info("PID %d start %r", os.getpid(), request)
try:
    with executor.call(request, show=False, out_err=out_err) as status:
        logging.info("wait on %r", status)
        while status.exit_code is None:
            status.wait()
        logging.info("wait over on %r", status)
    show_outcome(status.outcome)
except Exception as exception:  # pragma: no cover
    logging.exception(exception)  # pragma: no cover
finally:
    logging.info("done")
    logging.shutdown()
