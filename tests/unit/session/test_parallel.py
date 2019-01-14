from __future__ import absolute_import, unicode_literals

import os


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
    assert result.ret == 0, "{}{}{}".format(result.err, os.linesep, result.out)


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
    assert result.ret == 0, "{}{}{}".format(result.err, os.linesep, result.out)


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
    assert result.ret == 1, result.out
    assert result.out == "ERROR: circular dependency detected: a | b\n"


def test_parallel_error_report(cmd, initproj):
    initproj(
        "pkg123-0.7",
        filedefs={
            "tox.ini": """
            [tox]
            isolated_build = true
            envlist = a
            [testenv]
            commands=python -c "import sys, os; sys.stderr.write(str(12345) + os.linesep);\
             raise SystemExit(17)"
        """,
            "pyproject.toml": """
            [build-system]
            requires = ["setuptools >= 35.0.2"]
            build-backend = 'setuptools.build_meta'
                        """,
        },
    )
    result = cmd("-p", "all")
    msg = result.out
    assert result.ret == 1, msg
    # we print output
    assert "(exited with code 17)" in result.out, msg
    assert "Failed a under process " in result.out, msg

    assert any(line for line in result.outlines if line == "12345")

    # single summary at end
    summary_lines = [j for j, l in enumerate(result.outlines) if " summary " in l]
    assert len(summary_lines) == 1, msg

    assert result.outlines[summary_lines[0] + 1 :] == ["ERROR:   a: parallel child exit code 1"]
