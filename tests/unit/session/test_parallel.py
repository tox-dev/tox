from __future__ import absolute_import, unicode_literals

import json
import os
import subprocess
import sys
import threading

import pytest
from flaky import flaky

from tox._pytestplugin import RunResult


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
    result = cmd("-p", "all")
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
    result = cmd("-p", "all", "-o")
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
    result = cmd("-p", "1")
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
            allowlist_externals = {}
        """.format(
                sys.executable,
            ),
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
allowlist_externals = {}
commands =
    python -c '[print("hello world") for _ in range(5000)]'
""".format(
        sys.executable,
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
allowlist_externals = {}
commands =
    python -c '[print("hello world") for _ in range(1)]'
""".format(
        sys.executable,
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
allowlist_externals = {}
commands =
    python -c 'import sys; sys.stderr.write("stderr env"); sys.stdout.write("stdout env")'

[testenv:e3]
commands =
    python -c 'import sys; sys.stderr.write("stderr always "); sys.stdout.write("stdout always ")'
parallel_show_output = True
""".format(
        sys.executable,
    )
    initproj("pkg123-0.7", filedefs={"tox.ini": tox_ini})
    result = cmd("-p", "all")
    result.assert_success()
    assert "stdout env" not in result.out, result.output()
    assert "stderr env" not in result.out, result.output()
    assert "stdout always" in result.out, result.output()
    assert "stderr always" in result.out, result.output()


@pytest.fixture()
def parallel_project(initproj):
    return initproj(
        "pkg123-0.7",
        filedefs={
            "tox.ini": """
            [tox]
            skipsdist = True
            envlist = a, b
            [testenv]
            skip_install = True
            commands=python -c "import sys; print(sys.executable)"
        """,
        },
    )


def test_parallel_no_spinner_on(cmd, parallel_project, monkeypatch):
    monkeypatch.setenv(str("TOX_PARALLEL_NO_SPINNER"), str("1"))
    result = cmd("-p", "all")
    result.assert_success()
    assert "[2] a | b" not in result.out


def test_parallel_no_spinner_off(cmd, parallel_project, monkeypatch):
    monkeypatch.setenv(str("TOX_PARALLEL_NO_SPINNER"), str("0"))
    result = cmd("-p", "all")
    result.assert_success()
    assert "[2] a | b" in result.out


def test_parallel_no_spinner_not_set(cmd, parallel_project, monkeypatch):
    monkeypatch.delenv(str("TOX_PARALLEL_NO_SPINNER"), raising=False)
    result = cmd("-p", "all")
    result.assert_success()
    assert "[2] a | b" in result.out


def test_parallel_result_json(cmd, parallel_project, tmp_path):
    parallel_result_json = tmp_path / "parallel.json"
    result = cmd("-p", "all", "--result-json", "{}".format(parallel_result_json))
    ensure_result_json_ok(result, parallel_result_json)


def ensure_result_json_ok(result, json_path):
    if isinstance(result, RunResult):
        result.assert_success()
    else:
        assert not isinstance(result, subprocess.CalledProcessError)
    assert json_path.exists()
    serial_data = json.loads(json_path.read_text())
    ensure_key_in_env(serial_data)


def ensure_key_in_env(serial_data):
    for env in ("a", "b"):
        for key in ("setup", "test"):
            assert key in serial_data["testenvs"][env], json.dumps(
                serial_data["testenvs"],
                indent=2,
            )


def test_parallel_result_json_concurrent(cmd, parallel_project, tmp_path):
    # first run to set up the environments (env creation is not thread safe)
    result = cmd("-p", "all")
    result.assert_success()

    invoke_result = {}

    def invoke_tox_in_thread(thread_name, result_json):
        try:
            # needs to be process to have it's own stdout
            invoke_result[thread_name] = subprocess.check_output(
                [sys.executable, "-m", "tox", "-p", "all", "--result-json", str(result_json)],
                universal_newlines=True,
            )
        except subprocess.CalledProcessError as exception:
            invoke_result[thread_name] = exception

    # now concurrently
    parallel1_result_json = tmp_path / "parallel1.json"
    parallel2_result_json = tmp_path / "parallel2.json"
    threads = [
        threading.Thread(target=invoke_tox_in_thread, args=(k, p))
        for k, p in (("t1", parallel1_result_json), ("t2", parallel2_result_json))
    ]
    [t.start() for t in threads]
    [t.join() for t in threads]

    ensure_result_json_ok(invoke_result["t1"], parallel1_result_json)
    ensure_result_json_ok(invoke_result["t2"], parallel2_result_json)
    # our set_os_env_var is not thread-safe so clean-up TOX_WORK_DIR
    os.environ.pop("TOX_WORK_DIR", None)
