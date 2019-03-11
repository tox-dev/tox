import signal
import subprocess
import sys
import time

import pytest
from pathlib2 import Path


def test_provision_missing(initproj, cmd):
    initproj(
        "pkg123-0.7",
        filedefs={
            "tox.ini": """
                    [tox]
                    skipsdist=True
                    minversion = 3.7.0
                    requires = setuptools == 40.6.3
                    [testenv]
                    commands=python -c "import sys; print(sys.executable); raise SystemExit(1)"
                """
        },
    )
    result = cmd("-q", "-q")
    assert result.ret == 1
    meta_python = Path(result.out.strip())
    assert meta_python.exists()


@pytest.mark.skipif(
    sys.platform == "win32", reason="no easy way to trigger CTRL+C on windows for a process"
)
def test_provision_interrupt_child(initproj, cmd):
    initproj(
        "pkg123-0.7",
        filedefs={
            "tox.ini": """
                    [tox]
                    skipsdist=True
                    minversion = 3.7.0
                    requires = setuptools == 40.6.3
                    [testenv]
                    commands=python -c "file_h = open('a', 'w').write('b'); \
                    import time; time.sleep(10)"
                    [testenv:b]
                    basepython=python
                """
        },
    )
    cmd = [sys.executable, "-m", "tox", "-v", "-v", "-e", "python"]
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True
    )
    signal_file = Path() / "a"
    while not signal_file.exists() and process.poll() is None:
        time.sleep(0.1)
    if process.poll() is not None:
        out, err = process.communicate()
        assert False, out

    process.send_signal(signal.SIGINT)
    out, _ = process.communicate()
    assert "\nERROR: keyboardinterrupt\n" in out, out
