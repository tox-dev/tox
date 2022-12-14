import signal
import subprocess
import sys
import time

import pytest

if sys.version_info[:2] >= (3, 4):
    from pathlib import Path
else:
    from pathlib2 import Path

from tox.constants import INFO
from tox.util.main import MAIN_FILE


@pytest.mark.skipif(
    "sys.platform == 'win32' and sys.version_info < (3,)",
    reason="does not run on windows with py2",
)
def test_provision_missing(initproj, cmd):
    initproj(
        "pkg123-0.7",
        filedefs={
            "tox.ini": """\
                [tox]
                skipsdist=True
                minversion = 3.7.0,<4
                requires =
                    setuptools == 40.6.3
                [testenv]
                commands=python -c "import sys; print(sys.executable); raise SystemExit(1)"
            """,
        },
    )
    result = cmd("-e", "py")
    result.assert_fail()
    assert "tox.exception.InvocationError" not in result.output()
    assert not result.err
    assert ".tox create: " in result.out
    assert ".tox installdeps: " in result.out
    assert "py create: " in result.out

    at = next(at for at, l in enumerate(result.outlines) if l.startswith("py run-test: ")) + 1
    meta_python = Path(result.outlines[at])
    assert meta_python.exists()


@pytest.mark.skipif("sys.platform == 'win32'", reason="pyenv does not exists on Windows")
def test_provision_from_pyvenv(initproj, cmd, monkeypatch):
    initproj(
        "pkg123-0.7",
        filedefs={
            "tox.ini": """\
                [tox]
                skipsdist=True
                minversion = 3.7.0,<4
                requires =
                    setuptools == 40.6.3
                [testenv]
                commands=python -c "import sys; print(sys.executable); raise SystemExit(1)"
            """,
        },
    )
    monkeypatch.setenv(str("__PYVENV_LAUNCHER__"), sys.executable)
    result = cmd("-e", "py", "-vv")
    result.assert_fail()
    assert ".tox/.tox/bin/python -m virtualenv" in result.out


@pytest.mark.skipif(
    "sys.version_info < (3, 7)",
    reason="tox 4 only supports Python >= 3.7",
)
def test_provision_tox_4(initproj, cmd, monkeypatch):
    initproj(
        "pkg123-0.7",
        filedefs={
            "tox.ini": """\
                [tox]
                no_package=True
                min_version = 4
                [testenv]
                commands=python -c "import os; print('assert this')"
            """,
        },
    )
    result = cmd("-e", "py", "-vvv")
    # result.assert_success() has some assumptions about output that tox 4 doesn't follow
    assert result.ret == 0, result.output()
    assert "assert this" in result.out
    # this exact line is only in tox 3:
    assert "  congratulations :)" not in result.out.splitlines()


@pytest.mark.skipif(INFO.IS_PYPY, reason="TODO: process numbers work differently on pypy")
@pytest.mark.skipif(
    "sys.platform == 'win32'",
    reason="triggering SIGINT reliably on Windows is hard",
)
@pytest.mark.parametrize("signal_type", [signal.SIGINT, signal.SIGTERM])
def test_provision_interrupt_child(initproj, monkeypatch, capfd, signal_type):
    monkeypatch.delenv(str("PYTHONPATH"), raising=False)
    monkeypatch.setenv(str("TOX_REPORTER_TIMESTAMP"), str("1"))
    initproj(
        "pkg123-0.7",
        filedefs={
            "tox.ini": """
                    [tox]
                    skipsdist=True
                    minversion = 3.7.0,<4
                    requires = setuptools == 40.6.3
                               tox == 3.7.0
                    [testenv:b]
                    commands=python -c "import time; open('a', 'w').write('content'); \
                     time.sleep(10)"
                    basepython = python
                """,
        },
    )
    cmd = [sys.executable, MAIN_FILE, "-v", "-v", "-e", "b"]
    process = subprocess.Popen(
        cmd,
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

    signal_file = Path() / "a"
    while not signal_file.exists() and process.poll() is None:
        time.sleep(0.1)
    if process.poll() is not None:
        out, err = process.communicate()
        assert False, out

    all_process = []
    if current_process is not None:
        all_process.append(current_process)
        all_process.extend(current_process.children(recursive=False))
        # 1 process for the host tox, 1 for the provisioned
        assert len(all_process) >= 2, all_process

    process.send_signal(signal.CTRL_C_EVENT if sys.platform == "win32" else signal_type)
    process.communicate()
    out, err = capfd.readouterr()
    assert ".tox KeyboardInterrupt: from" in out, out

    for process in all_process:
        assert not process.is_running(), "{}{}".format(
            out,
            "\n".join(repr(i) for i in all_process),
        )


@pytest.mark.skipif("sys.platform == 'win32'", reason="pyenv does not exists on Windows")
def test_provision_race(initproj, cmd, monkeypatch):
    initproj(
        "pkg123-0.7",
        filedefs={
            "tox.ini": """\
                [tox]
                skipsdist=True
                minversion = 3.7.0,<4
                requires =
                    setuptools == 40.6.3
                [testenv]
                commands=python -c "import sys; print(sys.executable); raise SystemExit(1)"
                [testenv:x2]
            """,
        },
    )

    procs = [
        subprocess.Popen(
            [sys.executable, "-m", "tox", "-e", "py", "-vv"],
            stdout=subprocess.PIPE,
        )
        for _ in range(2)
    ]
    for proc in procs:
        stdout, stderr = proc.communicate()
        assert proc.returncode != 0
        assert b".tox/.tox/bin/python -m virtualenv" in stdout
