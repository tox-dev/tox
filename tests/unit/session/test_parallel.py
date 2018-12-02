import os


def test_parallel_live(cmd, initproj):
    initproj(
        "pkg123-0.7",
        filedefs={
            "tox.ini": """
            [tox]
            envlist = a, b
            [testenv]
            commands=python -c "import sys; print(sys.executable)"
        """
        },
    )
    result = cmd("--parallel", "--parallel-live")
    assert result.ret == 0, "{}{}{}".format(result.err, os.linesep, result.out)


def test_parallel(cmd, initproj):
    initproj(
        "pkg123-0.7",
        filedefs={
            "tox.ini": """
            [tox]
            envlist = a, b
            [testenv]
            commands=python -c "import sys; print(sys.executable)"
        """
        },
    )
    result = cmd("--parallel")
    assert result.ret == 0, "{}{}{}".format(result.err, os.linesep, result.out)
