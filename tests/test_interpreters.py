import sys
import os

import pytest
from tox.interpreters import *  # noqa
from tox.config import get_plugin_manager


@pytest.fixture
def interpreters():
    pm = get_plugin_manager()
    return Interpreters(hook=pm.hook)


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


def test_tox_get_python_executable():
    class envconfig:
        basepython = sys.executable
        envname = "pyxx"
    p = tox_get_python_executable(envconfig)
    assert p == py.path.local(sys.executable)
    for ver in [""] + "2.4 2.5 2.6 2.7 3.0 3.1 3.2 3.3".split():
        name = "python%s" % ver
        if sys.platform == "win32":
            pydir = "python%s" % ver.replace(".", "")
            x = py.path.local("c:\%s" % pydir)
            print(x)
            if not x.check():
                continue
        else:
            if not py.path.local.sysfind(name):
                continue
        envconfig.basepython = name
        p = tox_get_python_executable(envconfig)
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

    class envconfig:
        basepython = "1lk23j"
        envname = "pyxx"

    t = tox_get_python_executable(envconfig)
    assert t == "hello"


def test_run_and_get_interpreter_info():
    name = os.path.basename(sys.executable)
    info = run_and_get_interpreter_info(name, sys.executable)
    assert info.version_info == tuple(sys.version_info)
    assert info.name == name
    assert info.executable == sys.executable


class TestInterpreters:

    def test_get_executable(self, interpreters):
        class envconfig:
            basepython = sys.executable
            envname = "pyxx"

        x = interpreters.get_executable(envconfig)
        assert x == sys.executable
        info = interpreters.get_info(envconfig)
        assert info.version_info == tuple(sys.version_info)
        assert info.executable == sys.executable
        assert info.runnable

    def test_get_executable_no_exist(self, interpreters):
        class envconfig:
            basepython = "1lkj23"
            envname = "pyxx"
        assert not interpreters.get_executable(envconfig)
        info = interpreters.get_info(envconfig)
        assert not info.version_info
        assert info.name == "1lkj23"
        assert not info.executable
        assert not info.runnable

    def test_get_sitepackagesdir_error(self, interpreters):
        class envconfig:
            basepython = sys.executable
            envname = "123"
        info = interpreters.get_info(envconfig)
        s = interpreters.get_sitepackagesdir(info, "")
        assert s
