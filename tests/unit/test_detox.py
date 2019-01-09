import os
import subprocess
import sys


def test_has_detox_module():
    out = subprocess.check_output(
        [sys.executable, "-m", "detox", "--help"], universal_newlines=True
    )
    assert (
        "run tox environments in parallel, the argument controls limit: all, auto - "
        "cpu count, some positive number, zero is turn off (default: auto)" in out
    )


def test_has_detox_cli():
    out = subprocess.check_output(
        [
            os.path.join(
                os.path.dirname(sys.executable),
                "detox{}".format(".exe" if sys.executable.endswith(".exe") else ""),
            ),
            "--help",
        ],
        universal_newlines=True,
    )
    assert (
        "run tox environments in parallel, the argument controls limit: all, auto - cpu"
        " count, some positive number, zero is turn off (default: auto)" in out
    )
