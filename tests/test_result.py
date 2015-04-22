import sys
import py
from tox.result import ResultLog
import tox
import pytest


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
    assert replog.dict["host"] == py.std.socket.getfqdn()
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
    assert replog.dict["host"] == py.std.socket.getfqdn()
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
    envlog = replog.get_envlog("py26")
    envlog.set_python_info(py.path.local(sys.executable))
    assert envlog.dict["python"]["version_info"] == list(sys.version_info)
    assert envlog.dict["python"]["version"] == sys.version
    assert envlog.dict["python"]["executable"] == sys.executable


def test_get_commandlog(pkg):
    replog = ResultLog()
    replog.set_header(installpkg=pkg)
    envlog = replog.get_envlog("py26")
    assert "setup" not in envlog.dict
    setuplog = envlog.get_commandlog("setup")
    setuplog.add_command(["virtualenv", "..."], "venv created", 0)
    assert setuplog.list == [{"command": ["virtualenv", "..."],
                              "output": "venv created",
                              "retcode": "0"}]
    assert envlog.dict["setup"]
    setuplog2 = replog.get_envlog("py26").get_commandlog("setup")
    assert setuplog2.list == setuplog.list
