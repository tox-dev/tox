# type: ignore
import logging
import os
import signal
import sys
from io import TextIOWrapper
from pathlib import Path

from tox.execute import local_sub_process
from tox.execute.api import ToxKeyboardInterrupt
from tox.execute.request import StdinSource
from tox.report import NamedBytesIO

logging.basicConfig(level=logging.DEBUG, format="%(relativeCreated)d\t%(levelname).1s\t%(message)s")
bad_process = Path(__file__).parent / "bad_process.py"

executor = local_sub_process.LocalSubProcessExecutor(colored=False)
request = local_sub_process.ExecuteRequest(
    cmd=[sys.executable, bad_process, sys.argv[1]],
    cwd=Path().absolute(),
    env=os.environ.copy(),
    stdin=StdinSource.API,
)
out_err = TextIOWrapper(NamedBytesIO("out")), TextIOWrapper(NamedBytesIO("err"))


def show_outcome(outcome):
    print(outcome.exit_code)
    print(repr(outcome.out))
    print(repr(outcome.err))
    print(outcome.elapsed, end="")


def handler(s, f):
    print(f"{s} {f}")
    raise KeyboardInterrupt


signal.signal(signal.SIGINT, handler)
logging.info("PID %d start %r", os.getpid(), request)
try:
    with executor.call(request, show=False, out_err=out_err) as status:
        logging.info("wait on %r", status)
        while status.exit_code is None:
            status.wait()
        logging.info("wait over on %r", status)
    show_outcome(status.outcome)
except ToxKeyboardInterrupt as exception:
    show_outcome(exception.outcome)
except Exception as exception:
    logging.exception(exception)
finally:
    logging.info("done")
