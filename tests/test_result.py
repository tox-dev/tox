import os
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
@pytest.mark.parametrize('os_name', ['posix', 'nt'])
def test_invocation_error(exit_code, os_name, mocker, monkeypatch):
    monkeypatch.setattr(os, 'name', value=os_name)
    mocker.spy(tox, '_exit_code_str')
    if exit_code is None:
        exception = tox.exception.InvocationError("<command>")
    else:
        exception = tox.exception.InvocationError("<command>", exit_code)
    result = str(exception)
    # check that mocker works,
    # because it will be our only test in test_z_cmdline.py::test_exit_code
    # need the mocker.spy above
    assert tox._exit_code_str.call_count == 1
    assert tox._exit_code_str.call_args == mocker.call('InvocationError', "<command>", exit_code)
    if exit_code is None:
        needle = "(exited with code"
        assert needle not in result
    else:
        needle = "(exited with code %d)" % exit_code
        assert needle in result
        note = ("Note: this might indicate a fatal error signal")
        if (os_name == 'posix') and (exit_code == 128 + signal.SIGTERM):
            assert note in result
            number = signal.SIGTERM
            name = "SIGTERM"
            signal_str = "({} - 128 = {}: {})".format(exit_code, number, name)
            assert signal_str in result
        else:
            assert note not in result
