import distutils.spawn
import os
import subprocess
import sys

import py
import pytest

from tox.config import get_plugin_manager
from tox.interpreters import Interpreters
from tox.interpreters import run_and_get_interpreter_info
from tox.interpreters import tox_get_python_executable


@pytest.fixture
def interpreters():
    pm = get_plugin_manager()
    return Interpreters(hook=pm.hook)


@pytest.mark.skipif("sys.platform != 'win32'")
def test_locate_via_py(monkeypatch):
    from tox.interpreters import locate_via_py

    def fake_find_exe(exe):
        assert exe == 'py'
        return 'py'

    def fake_popen(cmd, stdout):
        assert cmd[:3] == ('py', '-3.2', '-c')

        class proc:
            returncode = 0

            @staticmethod
            def communicate():
                return sys.executable.encode(), None
        return proc

    # Monkeypatch modules to return our faked value
    monkeypatch.setattr(distutils.spawn, 'find_executable', fake_find_exe)
    monkeypatch.setattr(subprocess, 'Popen', fake_popen)
    assert locate_via_py('3', '2') == sys.executable


def test_tox_get_python_executable():
    class envconfig:
        basepython = sys.executable
        envname = "pyxx"
    p = tox_get_python_executable(envconfig)
    assert p == py.path.local(sys.executable)
    for ver in "2.7 3.4 3.5 3.6".split():
        name = "python%s" % ver
        if sys.platform == "win32":
            pydir = "python%s" % ver.replace(".", "")
            x = py.path.local(r"c:\%s" % pydir)
            print(x)
            if not x.check():
                continue
        else:
            if not py.path.local.sysfind(name):
                continue
        envconfig.basepython = name
        p = tox_get_python_executable(envconfig)
        assert p
        popen = subprocess.Popen([str(p), '-V'], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        stdout, stderr = popen.communicate()
        assert not stdout or not stderr
        assert ver in stderr.decode('ascii') or ver in stdout.decode('ascii')


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
