from __future__ import absolute_import, unicode_literals

import sys

import pytest
from flaky import flaky


def test_parallel(cmd, initproj):
    initproj(
        "pkg123-0.7",
        filedefs={
            "tox.ini": """
            [tox]
            envlist = a, b
            isolated_build = true
            [testenv]
            commands=python -c "import sys; print(sys.executable)"
            [testenv:b]
            depends = a
        """,
            "pyproject.toml": """
            [build-system]
            requires = ["setuptools >= 35.0.2"]
            build-backend = 'setuptools.build_meta'
                        """,
        },
    )
    result = cmd("--parallel", "all")
    result.assert_success()


@flaky(max_runs=3)
def test_parallel_live(cmd, initproj):
    initproj(
        "pkg123-0.7",
        filedefs={
            "tox.ini": """
            [tox]
            isolated_build = true
            envlist = a, b
            [testenv]
            commands=python -c "import sys; print(sys.executable)"
        """,
            "pyproject.toml": """
            [build-system]
            requires = ["setuptools >= 35.0.2"]
            build-backend = 'setuptools.build_meta'
                        """,
        },
    )
    result = cmd("--parallel", "all", "--parallel-live")
    result.assert_success()


def test_parallel_circular(cmd, initproj):
    initproj(
        "pkg123-0.7",
        filedefs={
            "tox.ini": """
            [tox]
            isolated_build = true
            envlist = a, b
            [testenv:a]
            depends = b
            [testenv:b]
            depends = a
        """,
            "pyproject.toml": """
            [build-system]
            requires = ["setuptools >= 35.0.2"]
            build-backend = 'setuptools.build_meta'
                        """,
        },
    )
    result = cmd("--parallel", "1")
    result.assert_fail()
    assert result.out == "ERROR: circular dependency detected: a | b\n"


@pytest.mark.parametrize("live", [True, False])
def test_parallel_error_report(cmd, initproj, monkeypatch, live):
    monkeypatch.setenv(str("_TOX_SKIP_ENV_CREATION_TEST"), str("1"))
    initproj(
        "pkg123-0.7",
        filedefs={
            "tox.ini": """
            [tox]
            isolated_build = true
            envlist = a
            [testenv]
            skip_install = true
            commands=python -c "import sys, os; sys.stderr.write(str(12345) + os.linesep);\
             raise SystemExit(17)"
            whitelist_externals = {}
        """.format(
                sys.executable
            )
        },
    )
    args = ["-o"] if live else []
    result = cmd("-p", "all", *args)
    result.assert_fail()
    msg = result.out
    # for live we print the failure logfile, otherwise just stream through (no logfile present)
    assert "(exited with code 17)" in result.out, msg
    if not live:
        assert "ERROR: invocation failed (exit code 1), logfile:" in result.out, msg
    assert any(line for line in result.outlines if line == "12345"), result.out

    # single summary at end
    summary_lines = [j for j, l in enumerate(result.outlines) if " summary " in l]
    assert len(summary_lines) == 1, msg

    assert result.outlines[summary_lines[0] + 1 :] == ["ERROR:   a: parallel child exit code 1"]


def test_parallel_deadlock(cmd, initproj, monkeypatch):
    monkeypatch.setenv(str("_TOX_SKIP_ENV_CREATION_TEST"), str("1"))
    tox_ini = """\
[tox]
envlist = e1,e2
skipsdist = true

[testenv]
whitelist_externals = {}
commands =
    python -c '[print("hello world") for _ in range(5000)]'
""".format(
        sys.executable
    )

    initproj("pkg123-0.7", filedefs={"tox.ini": tox_ini})
    cmd("-p", "2")  # used to hang indefinitely


def test_parallel_recreate(cmd, initproj, monkeypatch):
    monkeypatch.setenv(str("_TOX_SKIP_ENV_CREATION_TEST"), str("1"))
    tox_ini = """\
[tox]
envlist = e1,e2
skipsdist = true

[testenv]
whitelist_externals = {}
commands =
    python -c '[print("hello world") for _ in range(1)]'
""".format(
        sys.executable
    )
    cwd = initproj("pkg123-0.7", filedefs={"tox.ini": tox_ini})
    log_dir = cwd / ".tox" / "e1" / "log"
    assert not log_dir.exists()
    cmd("-p", "2")
    after = log_dir.listdir()
    assert len(after) >= 2

    res = cmd("-p", "2", "-rv")
    assert res
    end = log_dir.listdir()
    assert len(end) >= 3
    assert not ({f.basename for f in after} - {f.basename for f in end})


@flaky(max_runs=3)
def test_parallel_show_output(cmd, initproj, monkeypatch):
    monkeypatch.setenv(str("_TOX_SKIP_ENV_CREATION_TEST"), str("1"))
    tox_ini = """\
[tox]
envlist = e1,e2,e3
skipsdist = true

[testenv]
whitelist_externals = {}
commands =
    python -c 'import sys; sys.stderr.write("stderr env"); sys.stdout.write("stdout env")'

[testenv:e3]
commands =
    python -c 'import sys; sys.stderr.write("stderr always "); sys.stdout.write("stdout always ")'
parallel_show_output = True
""".format(
        sys.executable
    )
    initproj("pkg123-0.7", filedefs={"tox.ini": tox_ini})
    result = cmd("-p", "all")
    result.assert_success()
    assert "stdout env" not in result.out, result.output()
    assert "stderr env" not in result.out, result.output()
    assert "stdout always" in result.out, result.output()
    assert "stderr always" in result.out, result.output()
