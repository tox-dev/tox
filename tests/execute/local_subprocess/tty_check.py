from __future__ import annotations

import json
import shutil
import sys
from typing import Final

args = {
    "stdout": sys.stdout.isatty(),
    "stderr": sys.stderr.isatty(),
    "stdin": sys.stdin.isatty(),
    "terminal": shutil.get_terminal_size(fallback=(-1, -1)),
}
result: Final[str] = json.dumps(args)
print(result)  # ruff:ignore[print]  # test output
