import sys
import os

import pytest
from tox.interpreters import *

@pytest.fixture
def interpreters():
    return Interpreters()

@pytest.mark.skipif("sys.platform != 'win32'")
def test_locate_via_py(monkeypatch):
    class PseudoPy:
        def sysexec(self, *args):
            assert args[0] == '-3.2'
            assert args[1] == '-c'
            # Return value needs to actually exist!
            return sys.executable
    @staticmethod
    def ret_pseudopy(name):
        assert name == 'py'
        return PseudoPy()
    # Monkeypatch py.path.local.sysfind to return PseudoPy
    monkeypatch.setattr(py.path.local, 'sysfind', ret_pseudopy)
    assert locate_via_py('3', '2') == sys.executable

def test_find_executable():
    p = find_executable(sys.executable)
    assert p == py.path.local(sys.executable)
    for ver in [""] + "2.4 2.5 2.6 2.7 3.0 3.1 3.2 3.3".split():
        name = "python%s" % ver
        if sys.platform == "win32":
            pydir = "python%s" % ver.replace(".", "")
            x = py.path.local("c:\%s" % pydir)
            print (x)
            if not x.check():
                continue
        else:
            if not py.path.local.sysfind(name):
                continue
        p = find_executable(name)
        assert p
        popen = py.std.subprocess.Popen([str(p), '-V'],
                stderr=py.std.subprocess.PIPE)
        stdout, stderr = popen.communicate()
        assert ver in py.builtin._totext(stderr, "ascii")

def test_find_executable_extra(monkeypatch):
    @staticmethod
    def sysfind(x):
        return "hello"
    monkeypatch.setattr(py.path.local, "sysfind", sysfind)
    t = find_executable("qweqwe")
    assert t == "hello"

def test_run_and_get_interpreter_info():
    name = os.path.basename(sys.executable)
    info = run_and_get_interpreter_info(name, sys.executable)
    assert info.version_info == tuple(sys.version_info)
    assert info.name == name
    assert info.executable == sys.executable

class TestInterpreters:

    def test_get_info_self_exceptions(self, interpreters):
        pytest.raises(ValueError, lambda:
                      interpreters.get_info())
        pytest.raises(ValueError, lambda:
                      interpreters.get_info(name="12", executable="123"))

    def test_get_executable(self, interpreters):
        x = interpreters.get_executable(sys.executable)
        assert x == sys.executable
        assert not interpreters.get_executable("12l3k1j23")

    def test_get_info__name(self, interpreters):
        info = interpreters.get_info(executable=sys.executable)
        assert info.version_info == tuple(sys.version_info)
        assert info.executable == sys.executable
        assert info.runnable

    def test_get_info__name_not_exists(self, interpreters):
        info = interpreters.get_info("qlwkejqwe")
        assert not info.version_info
        assert info.name == "qlwkejqwe"
        assert not info.executable
        assert not info.runnable

    def test_get_sitepackagesdir_error(self, interpreters):
        info = interpreters.get_info(sys.executable)
        s = interpreters.get_sitepackagesdir(info, "")
        assert s
