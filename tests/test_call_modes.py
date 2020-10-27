import subprocess
import sys
from pathlib import Path

from tox.pytest import ToxProject


def test_call_as_module(empty_project: ToxProject) -> None:
    subprocess.check_output([sys.executable, "-m", "tox", "-h"])


def test_call_as_exe(empty_project: ToxProject) -> None:
    subprocess.check_output([str(Path(sys.executable).parent / "tox4"), "-h"])
