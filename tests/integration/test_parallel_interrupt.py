from __future__ import absolute_import, unicode_literals

import signal
import subprocess
import sys
from datetime import datetime

import pytest
from flaky import flaky

if sys.version_info[:2] >= (3, 4):
    from pathlib import Path
else:
    from pathlib2 import Path

from tox.constants import INFO
from tox.util.main import MAIN_FILE


@flaky(max_runs=3)
@pytest.mark.skipif(INFO.IS_PYPY, reason="TODO: process numbers work differently on pypy")
@pytest.mark.skipif(
    "sys.platform == 'win32'",
    reason="triggering SIGINT reliably on Windows is hard",
)
def test_parallel_interrupt(initproj, monkeypatch, capfd):
    monkeypatch.setenv(str("_TOX_SKIP_ENV_CREATION_TEST"), str("1"))
    monkeypatch.setenv(str("TOX_REPORTER_TIMESTAMP"), str("1"))
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
                    import time; time.sleep(100)"
                    allowlist_externals = {}

                """.format(
                sys.executable,
            ),
        },
    )
    process = subprocess.Popen(
        [sys.executable, MAIN_FILE, "-p", "all"],
        creationflags=(
            subprocess.CREATE_NEW_PROCESS_GROUP
            if sys.platform == "win32"
            else 0
            # needed for Windows signal send ability (CTRL+C)
        ),
    )
    try:
        import psutil

        current_process = psutil.Process(process.pid)
    except ImportError:
        current_process = None

    wait_for_env_startup(process)

    all_children = []
    if current_process is not None:
        all_children.append(current_process)
        all_children.extend(current_process.children(recursive=True))
        assert len(all_children) >= 1 + 2 + 2, all_children
    end = datetime.now() - start
    assert end
    process.send_signal(signal.CTRL_C_EVENT if sys.platform == "win32" else signal.SIGINT)
    process.wait()
    out, err = capfd.readouterr()
    output = "{}\n{}".format(out, err)
    assert "KeyboardInterrupt parallel - stopping children" in output, output
    assert "ERROR:   a: parallel child exit code " in output, output
    assert "ERROR:   b: parallel child exit code " in output, output
    for process in all_children:
        msg = "{}{}".format(output, "\n".join(repr(i) for i in all_children))
        assert not process.is_running(), msg


def wait_for_env_startup(process):
    """the environments will write files once they are up"""
    signal_files = [Path() / "a", Path() / "b"]
    found = False
    while True:
        if process.poll() is not None:
            break
        for signal_file in signal_files:
            if not signal_file.exists():
                break
        else:
            found = True
            break
    if not found or process.poll() is not None:
        missing = [f for f in signal_files if not f.exists()]
        out, _ = process.communicate()
        assert len(missing), out
        assert False, out
