from __future__ import annotations

import json
import shutil
import sys
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    import os

_ARGS: Final[dict[str, bool | os.terminal_size]] = {
    "stdout": sys.stdout.isatty(),
    "stderr": sys.stderr.isatty(),
    "stdin": sys.stdin.isatty(),
    "terminal": shutil.get_terminal_size(fallback=(-1, -1)),
}
_RESULT: Final[str] = json.dumps(_ARGS)
print(_RESULT)  # ruff:ignore[print]  # test output
