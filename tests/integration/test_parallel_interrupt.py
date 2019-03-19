from __future__ import absolute_import, unicode_literals

import signal
import subprocess
import sys
from datetime import datetime

from pathlib2 import Path

from tox import __main__ as main


def test_parallel_interrupt(initproj, cmd, monkeypatch):
    monkeypatch.setenv(str("_TOX_SKIP_ENV_CREATION_TEST"), str("1"))
    start = datetime.now()
    initproj(
        "pkg123-0.7",
        filedefs={
            "tox.ini": """
                    [tox]
                    envlist = a, b

                    [testenv]
                    skip_install = True
                    commands = python -c "open('{{envname}}', 'w').write('done'); \
                    import time; time.sleep(10)"
                    whitelist_externals = {}

                """.format(
                sys.executable
            )
        },
    )
    cmd = [sys.executable, main.__file__, "-v", "-v", "-p", "all", "-o"]
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True
    )
    try:
        import psutil

        current_process = psutil.Process(process.pid)
    except ImportError:
        current_process = None

    wait_for_env_startup(process)

    all_children = []
    if current_process is not None:
        all_children = current_process.children(recursive=True)
        assert all_children

    end = datetime.now() - start
    assert end
    process.send_signal(signal.CTRL_C_EVENT if sys.platform == "win32" else signal.SIGINT)
    out, _ = process.communicate()
    assert "keyboard interrupt parallel - stopping children" in out, out
    assert "\nERROR:   a: parallel child exit code " in out, out
    assert "\nERROR:   b: parallel child exit code " in out, out
    assert all(not children.is_running() for children in all_children)


def wait_for_env_startup(process):
    """the environments will write files once they are up"""
    signal_files = [Path() / "a", Path() / "b"]
    found = False
    while True:
        if all(signal_file.exists() for signal_file in signal_files):
            found = True
            break
        if process.poll() is not None:
            break
    if not found or process.poll() is not None:
        missing = [f for f in signal_files if not f.exists()]
        out, _ = process.communicate()
        assert len(missing), out
        assert False, out
