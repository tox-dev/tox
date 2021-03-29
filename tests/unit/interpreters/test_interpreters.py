from __future__ import unicode_literals

import os
import platform
import stat
import subprocess
import sys

import py
import pytest

import tox
from tox import reporter
from tox.config import get_plugin_manager
from tox.interpreters import (
    ExecFailed,
    InterpreterInfo,
    Interpreters,
    NoInterpreterInfo,
    run_and_get_interpreter_info,
    tox_get_python_executable,
)
from tox.reporter import Verbosity


@pytest.fixture(name="interpreters")
def create_interpreters_instance():
    pm = get_plugin_manager()
    return Interpreters(hook=pm.hook)


@pytest.mark.skipif(tox.INFO.IS_PYPY, reason="testing cpython interpreter discovery")
def test_tox_get_python_executable(mocker):
    class envconfig:
        basepython = sys.executable
        envname = "pyxx"
        config = mocker.MagicMock()
        config.return_value.option.return_value.discover = []

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
    for major, minor in [(2, 7), (3, 5), (3, 6), (3, 7), (3, 8)]:
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
    has_py_exe = py.path.local.sysfind("py") is not None
    for major in (2, 3):
        name = "python{}".format(major)
        if has_py_exe:
            error_code = subprocess.call(("py", "-{}".format(major), "-c", ""))
            if error_code:
                continue
        elif not py.path.local.sysfind(name):
            continue

        exe = get_exe(name)
        assert_version_in_output(exe, str(major))


@pytest.mark.skipif("sys.platform == 'win32'", reason="symlink execution unreliable on Windows")
def test_find_alias_on_path(monkeypatch, tmp_path, mocker):
    reporter.update_default_reporter(Verbosity.DEFAULT, Verbosity.DEBUG)
    magic = tmp_path / "magic{}".format(os.path.splitext(sys.executable)[1])
    os.symlink(sys.executable, str(magic))
    monkeypatch.setenv(
        str("PATH"),
        os.pathsep.join([str(tmp_path)] + os.environ.get(str("PATH"), "").split(os.pathsep)),
    )

    class envconfig:
        basepython = "magic"
        envname = "pyxx"
        config = mocker.MagicMock()
        config.return_value.option.return_value.discover = []

    detected = py.path.local.sysfind("magic")
    assert detected

    t = tox_get_python_executable(envconfig).lower()
    assert t == str(magic).lower()


def test_run_and_get_interpreter_info():
    name = os.path.basename(sys.executable)
    info = run_and_get_interpreter_info(name, sys.executable)
    assert info.version_info == tuple(sys.version_info)
    assert info.implementation == platform.python_implementation()
    assert info.executable == sys.executable


class TestInterpreters:
    def test_get_executable(self, interpreters, mocker):
        class envconfig:
            basepython = sys.executable
            envname = "pyxx"
            config = mocker.MagicMock()
            config.return_value.option.return_value.discover = []

        x = interpreters.get_executable(envconfig)
        assert x == sys.executable
        info = interpreters.get_info(envconfig)
        assert info.version_info == tuple(sys.version_info)
        assert info.executable == sys.executable
        assert isinstance(info, InterpreterInfo)

    def test_get_executable_no_exist(self, interpreters, mocker):
        class envconfig:
            basepython = "1lkj23"
            envname = "pyxx"
            config = mocker.MagicMock()
            config.return_value.option.return_value.discover = []

        assert not interpreters.get_executable(envconfig)
        info = interpreters.get_info(envconfig)
        assert not info.version_info
        assert info.name == "1lkj23"
        assert not info.executable
        assert isinstance(info, NoInterpreterInfo)

    @pytest.mark.skipif("sys.platform == 'win32'", reason="Uses a unix only wrapper")
    def test_get_info_uses_hook_path(self, tmp_path):
        magic = tmp_path / "magic{}".format(os.path.splitext(sys.executable)[1])
        wrapper = (
            "#!{executable}\n"
            "import subprocess\n"
            "import sys\n"
            'sys.exit(subprocess.call(["{executable}"] + sys.argv[1:]))\n'
        ).format(executable=sys.executable)
        magic.write_text(wrapper)
        magic.chmod(magic.stat().st_mode | stat.S_IEXEC)

        class MockHook:
            def tox_get_python_executable(self, envconfig):
                return str(magic)

        class envconfig:
            basepython = sys.executable
            envname = "magicpy"

        # Check that the wrapper is working first.
        # If it isn't, the default is to return the passed path anyway.
        subprocess.check_call([str(magic), "--help"])

        interpreters = Interpreters(hook=MockHook())
        info = interpreters.get_info(envconfig)
        assert info.executable == str(magic)

    def test_get_sitepackagesdir_error(self, interpreters, mocker):
        class envconfig:
            basepython = sys.executable
            envname = "123"
            config = mocker.MagicMock()
            config.return_value.option.return_value.discover = []

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
        implementation="CPython",
        executable="my-executable",
        version_info="my-version-info",
        sysplatform="my-sys-platform",
    ):
        return InterpreterInfo(
            implementation, executable, version_info, sysplatform, True, "/", None
        )

    def test_data(self):
        x = self.info("larry", "moe", "shemp", "curly")
        assert x.implementation == "larry"
        assert x.executable == "moe"
        assert x.version_info == "shemp"
        assert x.sysplatform == "curly"

    def test_str(self):
        x = self.info(executable="foo", version_info="bar")
        assert str(x) == "<executable at foo, version_info bar>"


class TestNoInterpreterInfo:
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
