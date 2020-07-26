import logging
import os
import sys
from pathlib import Path

from tox.execute import local_sub_process
from tox.execute.api import ToxKeyboardInterrupt

logging.basicConfig(level=logging.NOTSET)
bad_process = Path(__file__).parent / "bad_process.py"

executor = local_sub_process.LocalSubProcessExecutor()
local_sub_process.WAIT_GENERAL = 0.05
request = local_sub_process.ExecuteRequest(
    cmd=[sys.executable, bad_process, sys.argv[1], sys.argv[2], str(local_sub_process.WAIT_GENERAL * 3)],
    cwd=Path().absolute(),
    env=os.environ,
    allow_stdin=False,
)


try:
    executor(request, show_on_standard=False, colored=False)
except ToxKeyboardInterrupt as exception:
    outcome = exception.outcome
    print(outcome.exit_code)
    print(repr(outcome.out))
    print(repr(outcome.err))
    print(outcome.elapsed, end="")
