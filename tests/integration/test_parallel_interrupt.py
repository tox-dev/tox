from __future__ import absolute_import, unicode_literals

import signal
import subprocess
import sys
from datetime import datetime

from pathlib2 import Path


def test_parallel_interrupt(initproj, cmd):

    start = datetime.now()
    initproj(
        "pkg123-0.7",
        filedefs={
            "tox.ini": """
                    [tox]
                    skipsdist=True
                    envlist = a, b
                    [testenv]
                    commands = python -c "open('{envname}', 'w').write('done'); \
                     import time; time.sleep(3)"

                """
        },
    )
    cmd = [sys.executable, "-m", "tox", "-v", "-v", "-p", "all"]
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True
    )
    try:
        import psutil

        current_process = psutil.Process(process.pid)
    except ImportError:
        current_process = None

    # we wait until all environments are up and running
    signal_files = [Path() / "a", Path() / "b"]
    found = False
    while True:
        if all(signal_file.exists() for signal_file in signal_files):
            found = True
            break
        if process.poll() is not None:
            break
    if not found:
        out, _ = process.communicate()
        out = out.encode("utf-8")
        missing = [f for f in signal_files if not f.exists()]
        assert len(missing), out

    if current_process:
        all_children = current_process.children(recursive=True)
        assert all_children

    end = datetime.now() - start
    assert end
    process.send_signal(signal.CTRL_C_EVENT if sys.platform == "win32" else signal.SIGINT)
    out, _ = process.communicate()
    assert "\nERROR:   a: parallel child exit code " in out, out
    assert "\nERROR:   b: parallel child exit code " in out, out

    if current_process:
        assert all(not children.is_running() for children in all_children)
