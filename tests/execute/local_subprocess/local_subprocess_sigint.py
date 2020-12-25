# type: ignore
import logging
import os
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
local_sub_process.WAIT_GENERAL = 0.05
request = local_sub_process.ExecuteRequest(
    cmd=[sys.executable, bad_process, sys.argv[1], sys.argv[2], str(local_sub_process.WAIT_GENERAL * 3)],
    cwd=Path().absolute(),
    env=os.environ.copy(),
    stdin=StdinSource.API,
)
out_err = TextIOWrapper(NamedBytesIO("out")), TextIOWrapper(NamedBytesIO("err"))

try:
    with executor.call(request, show=False, out_err=out_err) as status:
        pass
except ToxKeyboardInterrupt as exception:
    outcome = exception.outcome
    print(outcome.exit_code)
    print(repr(outcome.out))
    print(repr(outcome.err))
    print(outcome.elapsed, end="")
