import subprocess
import sys
from pathlib import Path


def test_call_as_module(empty_project):
    subprocess.check_output([sys.executable, "-m", "tox", "-h"])


def test_call_as_exe(empty_project):
    subprocess.check_output([Path(sys.executable).parent / "tox", "-h"])
