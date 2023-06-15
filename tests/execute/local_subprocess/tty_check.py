from __future__ import annotations

import json
import shutil
import sys

args = {
    "stdout": sys.stdout.isatty(),
    "stderr": sys.stderr.isatty(),
    "stdin": sys.stdin.isatty(),
    "terminal": shutil.get_terminal_size(fallback=(-1, -1)),
}
result = json.dumps(args)
print(result)  # noqa: T201
