# pragma: no cover  # setup not built by tests
from __future__ import annotations

import os
import signal
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import FrameType

out = sys.stdout


def handler(signum: int, _: FrameType | None) -> None:
    _p(f"how about no signal {signum!r}")


def _p(m: str) -> None:
    out.write(f"{m}{os.linesep}")
    out.flush()  # force output flush in case we get killed


_p(f"start {__name__} with {sys.argv!r}")
signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)

_START_FILE = Path(sys.argv[1])
_p(f"create {_START_FILE}")
_START_FILE.write_text("", encoding="utf-8")
_p(f"created {_START_FILE}")
try:
    while True:
        time.sleep(0.01)
finally:
    _p(f"done {__name__}")
