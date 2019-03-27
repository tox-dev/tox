import pytest


# TODO
@pytest.mark.skip(reason="needs jython and dev cut of virtualenv")
def test_jython_create(initproj, cmd):
    initproj(
        "py_jython-0.1",
        filedefs={
            "tox.ini": """
                        [tox]
                        skipsdist = true
                        envlist = jython
                        commands = python -c 'import sys; print(sys.executable)'
                    """
        },
    )
    result = cmd("--notest", "-vvv")
    result.assert_success()
