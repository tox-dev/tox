import distutils.spawn
import os
import subprocess
import sys

import py
import pytest

import tox
from tox._pytestplugin import mark_dont_run_on_posix
from tox.config import get_plugin_manager
from tox.interpreters import (
    ExecFailed,
    InterpreterInfo,
    Interpreters,
    NoInterpreterInfo,
    run_and_get_interpreter_info,
    tox_get_python_executable,
)


@pytest.fixture(name="interpreters")
def create_interpreters_instance():
    pm = get_plugin_manager()
    return Interpreters(hook=pm.hook)


@mark_dont_run_on_posix
def test_locate_via_py(monkeypatch):
    from tox.interpreters import locate_via_py

    def fake_find_exe(exe):
        assert exe == "py"
        return "py"

    def fake_popen(cmd, stdout, stderr):
        fake_popen.last_call = cmd[:3]

        # need to pipe all stdout to collect the version information & need to
        # do the same for stderr output to avoid it being forwarded as the
        # current process's output, e.g. when the python launcher reports the
        # requested Python interpreter not being installed on the system
        assert stdout is subprocess.PIPE
        assert stderr is subprocess.PIPE

        class proc:
            returncode = 0

            @staticmethod
            def communicate():
                return sys.executable.encode(), None

        return proc

    monkeypatch.setattr(distutils.spawn, "find_executable", fake_find_exe)
    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    assert locate_via_py("3", "6") == sys.executable
    assert fake_popen.last_call == ("py", "-3.6", "-c")
    assert locate_via_py("3") == sys.executable
    assert fake_popen.last_call == ("py", "-3", "-c")


def test_tox_get_python_executable():
    class envconfig:
        basepython = sys.executable
        envname = "pyxx"

    def get_exe(name):
        envconfig.basepython = name
        p = tox_get_python_executable(envconfig)
        assert p
        return str(p)

    def assert_version_in_output(exe, version):
        out = subprocess.check_output((exe, "-V"), stderr=subprocess.STDOUT)
        assert version in out.decode()

    p = tox_get_python_executable(envconfig)
    assert p == py.path.local(sys.executable)
    for major, minor in tox.PYTHON.CPYTHON_VERSION_TUPLES:
        name = "python{}.{}".format(major, minor)
        if tox.INFO.IS_WIN:
            pydir = "python{}{}".format(major, minor)
            x = py.path.local(r"c:\{}".format(pydir))
            if not x.check():
                continue
        else:
            if not py.path.local.sysfind(name) or subprocess.call((name, "-c", "")):
                continue
        exe = get_exe(name)
        assert_version_in_output(exe, "{}.{}".format(major, minor))

    for major in (2, 3):
        name = "python{}".format(major)
        if tox.INFO.IS_WIN:
            if subprocess.call(("py", "-{}".format(major), "-c", "")):
                continue
        elif not py.path.local.sysfind(name):
            continue

        exe = get_exe(name)
        assert_version_in_output(exe, str(major))


def test_find_executable_extra(monkeypatch):
    @staticmethod
    def sysfind(_):
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


def test_exec_failed():
    x = ExecFailed("my-executable", "my-source", "my-out", "my-err")
    assert isinstance(x, Exception)
    assert x.executable == "my-executable"
    assert x.source == "my-source"
    assert x.out == "my-out"
    assert x.err == "my-err"


class TestInterpreterInfo:
    @staticmethod
    def info(
        name="my-name",
        executable="my-executable",
        version_info="my-version-info",
        sysplatform="my-sys-platform",
    ):
        return InterpreterInfo(name, executable, version_info, sysplatform)

    def test_runnable(self):
        assert self.info().runnable

    @pytest.mark.parametrize("missing_arg", ("executable", "version_info"))
    def test_assert_on_missing_args(self, missing_arg):
        with pytest.raises(AssertionError):
            self.info(**{missing_arg: None})

    def test_data(self):
        x = self.info("larry", "moe", "shemp", "curly")
        assert x.name == "larry"
        assert x.executable == "moe"
        assert x.version_info == "shemp"
        assert x.sysplatform == "curly"

    def test_str(self):
        x = self.info(executable="foo", version_info="bar")
        assert str(x) == "<executable at foo, version_info bar>"


class TestNoInterpreterInfo:
    def test_runnable(self):
        assert not NoInterpreterInfo("foo").runnable
        assert not NoInterpreterInfo("foo", executable=sys.executable).runnable

    def test_default_data(self):
        x = NoInterpreterInfo("foo")
        assert x.name == "foo"
        assert x.executable is None
        assert x.version_info is None
        assert x.out is None
        assert x.err == "not found"

    def test_set_data(self):
        x = NoInterpreterInfo("migraine", executable="my-executable", out="my-out", err="my-err")
        assert x.name == "migraine"
        assert x.executable == "my-executable"
        assert x.version_info is None
        assert x.out == "my-out"
        assert x.err == "my-err"

    def test_str_without_executable(self):
        x = NoInterpreterInfo("coconut")
        assert str(x) == "<executable not found for: coconut>"

    def test_str_with_executable(self):
        x = NoInterpreterInfo("coconut", executable="bang/em/together")
        assert str(x) == "<executable at bang/em/together, not runnable>"
