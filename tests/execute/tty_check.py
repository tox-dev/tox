import json
import shutil
import sys

print(
    json.dumps(
        {
            "stdout": sys.stdout.isatty(),
            "stderr": sys.stderr.isatty(),
            "stdin": sys.stdin.isatty(),
            "terminal": shutil.get_terminal_size(fallback=(-1, -1)),
        }
    )
)
