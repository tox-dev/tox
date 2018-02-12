import signal
import socket
import sys

import py
import pytest

import tox
from tox.result import ResultLog


@pytest.fixture
def pkg(tmpdir):
    p = tmpdir.join("hello-1.0.tar.gz")
    p.write("whatever")
    return p


def test_pre_set_header(pkg):
    replog = ResultLog()
    d = replog.dict
    assert replog.dict == d
    assert replog.dict["reportversion"] == "1"
    assert replog.dict["toxversion"] == tox.__version__
    assert replog.dict["platform"] == sys.platform
    assert replog.dict["host"] == socket.getfqdn()
    data = replog.dumps_json()
    replog2 = ResultLog.loads_json(data)
    assert replog2.dict == replog.dict


def test_set_header(pkg):
    replog = ResultLog()
    d = replog.dict
    replog.set_header(installpkg=pkg)
    assert replog.dict == d
    assert replog.dict["reportversion"] == "1"
    assert replog.dict["toxversion"] == tox.__version__
    assert replog.dict["platform"] == sys.platform
    assert replog.dict["host"] == socket.getfqdn()
    assert replog.dict["installpkg"] == {
        "basename": "hello-1.0.tar.gz",
        "md5": pkg.computehash("md5"),
        "sha256": pkg.computehash("sha256")}
    data = replog.dumps_json()
    replog2 = ResultLog.loads_json(data)
    assert replog2.dict == replog.dict


def test_addenv_setpython(pkg):
    replog = ResultLog()
    replog.set_header(installpkg=pkg)
    envlog = replog.get_envlog("py36")
    envlog.set_python_info(py.path.local(sys.executable))
    assert envlog.dict["python"]["version_info"] == list(sys.version_info)
    assert envlog.dict["python"]["version"] == sys.version
    assert envlog.dict["python"]["executable"] == sys.executable


def test_get_commandlog(pkg):
    replog = ResultLog()
    replog.set_header(installpkg=pkg)
    envlog = replog.get_envlog("py36")
    assert "setup" not in envlog.dict
    setuplog = envlog.get_commandlog("setup")
    setuplog.add_command(["virtualenv", "..."], "venv created", 0)
    assert setuplog.list == [{"command": ["virtualenv", "..."],
                              "output": "venv created",
                              "retcode": "0"}]
    assert envlog.dict["setup"]
    setuplog2 = replog.get_envlog("py36").get_commandlog("setup")
    assert setuplog2.list == setuplog.list


@pytest.mark.parametrize('exit_code', [None, 0, 5, 128 + signal.SIGTERM, 1234])
def test_invocation_error(exit_code):
    if exit_code is None:
        exception = tox.exception.InvocationError("<command>")
    else:
        exception = tox.exception.InvocationError("<command>", exit_code)
    result = str(exception)
    if exit_code is None:
        needle = "(exited with code"
        assert needle not in result
    else:
        needle = "(exited with code %d)" % exit_code
        assert needle in result
        if exit_code > 128:
            needle = ("Note: On unix systems, an exit code larger than 128 often "
                      "means a fatal error signal")
            assert needle in result
            if exit_code == 128 + signal.SIGTERM:
                eg_number = signal.SIGTERM
                eg_name = "SIGTERM"
            else:
                eg_number = 11
                eg_name = "SIGSEGV"
            eg_str = "(e.g. {}=128+{}: {})".format(eg_number+128, eg_number, eg_name)
            assert eg_str in result
