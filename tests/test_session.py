import os
import re
import sys
from threading import Thread

import pytest

import tox
from tox import venv
from tox.exception import MissingDependency, MissingDirectory
from tox.venv import CreationConfig, VirtualEnv, getdigest


def test__resolve_pkg_missing_directory(tmpdir, mocksession):
    distshare = tmpdir.join("distshare")
    spec = distshare.join("pkg123-*")
    with pytest.raises(MissingDirectory):
        mocksession._resolve_package(spec)


def test__resolve_pkg_missing_directory_in_distshare(tmpdir, mocksession):
    distshare = tmpdir.join("distshare")
    spec = distshare.join("pkg123-*")
    distshare.ensure(dir=1)
    with pytest.raises(MissingDependency):
        mocksession._resolve_package(spec)


def test__resolve_pkg_multiple_valid_versions(tmpdir, mocksession):
    distshare = tmpdir.join("distshare")
    distshare.ensure("pkg123-1.3.5.zip")
    p = distshare.ensure("pkg123-1.4.5.zip")
    result = mocksession._resolve_package(distshare.join("pkg123-*"))
    assert result == p
    mocksession.report.expect("info", "determin*pkg123*")


def test__resolve_pkg_with_invalid_version(tmpdir, mocksession):
    distshare = tmpdir.join("distshare")

    distshare.ensure("pkg123-1.something_bad.zip")
    distshare.ensure("pkg123-1.3.5.zip")
    p = distshare.ensure("pkg123-1.4.5.zip")

    result = mocksession._resolve_package(distshare.join("pkg123-*"))
    mocksession.report.expect("warning", "*1.something_bad*")
    assert result == p


def test__resolve_pkg_with_alpha_version(tmpdir, mocksession):
    distshare = tmpdir.join("distshare")
    distshare.ensure("pkg123-1.3.5.zip")
    distshare.ensure("pkg123-1.4.5a1.tar.gz")
    p = distshare.ensure("pkg123-1.4.5.zip")
    result = mocksession._resolve_package(distshare.join("pkg123-*"))
    assert result == p


def test__resolve_pkg_doubledash(tmpdir, mocksession):
    distshare = tmpdir.join("distshare")
    p = distshare.ensure("pkg-mine-1.3.0.zip")
    res = mocksession._resolve_package(distshare.join("pkg-mine*"))
    assert res == p
    distshare.ensure("pkg-mine-1.3.0a1.zip")
    res = mocksession._resolve_package(distshare.join("pkg-mine*"))
    assert res == p


def test_minversion(cmd, initproj):
    initproj(
        "interp123-0.5",
        filedefs={
            "tests": {"test_hello.py": "def test_hello(): pass"},
            "tox.ini": """
            [tox]
            minversion = 6.0
        """,
        },
    )
    result = cmd("-v")
    assert re.match(
        r"ERROR: MinVersionError: tox version is .*," r" required is at least 6.0", result.out
    )
    assert result.ret


def mock_venv(monkeypatch):
    """This creates a mock virtual environment (e.g. will inherit the current interpreter).

    Note: because we inherit, to keep things sane you must call the py environment and only that;
    and cannot install any packages. """

    class ProxyCurrentPython:
        @classmethod
        def readconfig(cls, path):
            assert path.dirname.endswith("{}py".format(os.sep))
            return CreationConfig(
                md5=getdigest(sys.executable),
                python=sys.executable,
                version=tox.__version__,
                sitepackages=False,
                usedevelop=False,
                deps=[],
                alwayscopy=False,
            )

    monkeypatch.setattr(CreationConfig, "readconfig", ProxyCurrentPython.readconfig)

    def venv_lookup(venv, name):
        assert name == "python"
        return sys.executable

    monkeypatch.setattr(VirtualEnv, "_venv_lookup", venv_lookup)

    @tox.hookimpl
    def tox_runenvreport(venv, action):
        return []

    monkeypatch.setattr(venv, "tox_runenvreport", tox_runenvreport)


def isolate_env_test(initproj, cmd, monkeypatch, env_var):
    initproj(
        "env_var_test",
        filedefs={
            "tox.ini": """
                       [tox]
                       skipsdist = True
                       [testenv]
                       commands = python -c "import os; print(os.environ['{}'])"
                   """.format(
                env_var
            )
        },
    )

    res = {"RESULT": None}

    class EnvironmentTestRun(Thread):
        """we wrap this invocation into a thread to avoid modifying in any way the
         current threads environment variable (e.g. on failure of this test incorrect teardown)"""

        def run(self):
            mock_venv(monkeypatch)
            res["RESULT"] = cmd("-q", "-e", "py").outlines

    thread = EnvironmentTestRun()
    thread.start()
    thread.join()
    return res["RESULT"]


def test_tox_work_dir_env_var_injected(initproj, cmd, monkeypatch):
    res = isolate_env_test(initproj, cmd, monkeypatch, "TOX_WORK_DIR")
    assert res[0] == os.path.join(os.getcwd(), ".tox")


def test_tox_env_name_env_var_injected(initproj, cmd, monkeypatch):
    res = isolate_env_test(initproj, cmd, monkeypatch, "TOX_ENV_NAME")
    assert res[0] == "py"


def test_tox_env_work_dir_env_var_injected(initproj, cmd, monkeypatch):
    res = isolate_env_test(initproj, cmd, monkeypatch, "TOX_ENV_WORK_DIR")
    assert res[0] == os.path.join(os.getcwd(), ".tox", "py")
