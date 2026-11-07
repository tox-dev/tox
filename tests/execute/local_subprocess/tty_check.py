from __future__ import annotations

import json
import shutil
import sys
from typing import Final

ARGS = {
    "stdout": sys.stdout.isatty(),
    "stderr": sys.stderr.isatty(),
    "stdin": sys.stdin.isatty(),
    "terminal": shutil.get_terminal_size(fallback=(-1, -1)),
}
RESULT: Final[str] = json.dumps(ARGS)
print(RESULT)  # ruff:ignore[print]  # test output
