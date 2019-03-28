import os
import signal
import socket
import sys

import py
import pytest

import tox
from tox.logs import ResultLog


@pytest.fixture(name="pkg")
def create_fake_pkg(tmpdir):
    pkg = tmpdir.join("hello-1.0.tar.gz")
    pkg.write("whatever")
    return pkg


def test_pre_set_header():
    replog = ResultLog()
    d = replog.dict
    assert replog.dict == d
    assert replog.dict["reportversion"] == "1"
    assert replog.dict["toxversion"] == tox.__version__
    assert replog.dict["platform"] == sys.platform
    assert replog.dict["host"] == socket.getfqdn()
    data = replog.dumps_json()
    replog2 = ResultLog.from_json(data)
    assert replog2.dict == replog.dict


def test_set_header(pkg):
    replog = ResultLog()
    d = replog.dict
    assert replog.dict == d
    assert replog.dict["reportversion"] == "1"
    assert replog.dict["toxversion"] == tox.__version__
    assert replog.dict["platform"] == sys.platform
    assert replog.dict["host"] == socket.getfqdn()
    expected = {
        "basename": "hello-1.0.tar.gz",
        "md5": pkg.computehash("md5"),
        "sha256": pkg.computehash("sha256"),
    }
    env_log = replog.get_envlog("a")
    env_log.set_header(installpkg=pkg)
    assert env_log.dict["installpkg"] == expected

    data = replog.dumps_json()
    replog2 = ResultLog.from_json(data)
    assert replog2.dict == replog.dict


def test_addenv_setpython(pkg):
    replog = ResultLog()
    envlog = replog.get_envlog("py36")
    envlog.set_python_info(py.path.local(sys.executable))
    envlog.set_header(installpkg=pkg)
    assert envlog.dict["python"]["version_info"] == list(sys.version_info)
    assert envlog.dict["python"]["version"] == sys.version
    assert envlog.dict["python"]["executable"] == sys.executable


def test_get_commandlog(pkg):
    replog = ResultLog()
    envlog = replog.get_envlog("py36")
    assert "setup" not in envlog.dict
    setuplog = envlog.get_commandlog("setup")
    envlog.set_header(installpkg=pkg)
    setuplog.add_command(["virtualenv", "..."], "venv created", 0)
    expected = [{"command": ["virtualenv", "..."], "output": "venv created", "retcode": 0}]
    assert setuplog.list == expected
    assert envlog.dict["setup"]
    setuplog2 = replog.get_envlog("py36").get_commandlog("setup")
    assert setuplog2.list == setuplog.list


@pytest.mark.parametrize("exit_code", [None, 0, 5, 128 + signal.SIGTERM, 1234])
@pytest.mark.parametrize("os_name", ["posix", "nt"])
def test_invocation_error(exit_code, os_name, mocker, monkeypatch):
    monkeypatch.setattr(os, "name", value=os_name)
    mocker.spy(tox.exception, "exit_code_str")
    result = str(tox.exception.InvocationError("<command>", exit_code=exit_code))
    # check that mocker works, because it will be our only test in
    # test_z_cmdline.py::test_exit_code needs the mocker.spy above
    assert tox.exception.exit_code_str.call_count == 1
    call_args = tox.exception.exit_code_str.call_args
    assert call_args == mocker.call("InvocationError", "<command>", exit_code)
    if exit_code is None:
        assert "(exited with code" not in result
    else:
        assert "(exited with code %d)" % exit_code in result
        note = "Note: this might indicate a fatal error signal"
        if (os_name == "posix") and (exit_code == 128 + signal.SIGTERM):
            assert note in result
            assert "({} - 128 = {}: SIGTERM)".format(exit_code, signal.SIGTERM) in result
        else:
            assert note not in result
